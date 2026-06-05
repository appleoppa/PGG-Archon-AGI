from __future__ import annotations

import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from agent.pgg_archon_minimax_structured_adapter import parse_structured_json

REQUIRED_KEYS = ("id", "title", "key_thesis", "mapped_skill", "status", "providers_seen")


def _strip_fence(t: str) -> str:
    s = t.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
        s = re.sub(r"\s*```$", "", s)
    return s


def _try_parse_json_obj(t: str) -> dict[str, Any] | None:
    s = _strip_fence(t)
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else None
    except Exception:
        pass
    a = s.find("{")
    b = s.rfind("}")
    if a >= 0 and b > a:
        try:
            v = json.loads(s[a:b+1])
            return v if isinstance(v, dict) else None
        except Exception:
            pass
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    v = json.loads(s[start:i+1])
                    return v if isinstance(v, dict) else None
                except Exception:
                    start = -1
    return None


def _has_required(d: dict[str, Any]) -> bool:
    return all(k in d for k in REQUIRED_KEYS)


_PROVIDERS = [
    ("deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1/chat/completions", "DEEPSEEK_V4_FLASH_API_KEY", "chat", 4096),
    ("agnes", "agnes-2.0-flash", "https://apihub.agnes-ai.com/v1/chat/completions", "AGNES_AI_API_KEY", "chat", 2200),
    ("minimax", "MiniMax-M3", "https://api.minimax.chat/v1/chat/completions", "MINIMAX_API_KEY", "chat", 2200),
    ("gpt55", "gpt-5.5", "https://chuangagent.eu.cc/v1/chat/completions", "GPT55_5YUANTOKEN_API_KEY", "chat", 4096),
]

_THIRD_PARTY_JUDGE_PROVIDERS = [
    ("mimo", "mimo-v2.5-pro", "https://token-plan-cn.xiaomimimo.com/v1/chat/completions", "MIMO_V25_PRO_API_KEY", "chat", 4096),
]


def _read_env(env: str) -> str:
    p = Path.home() / ".hermes/.env"
    for line in p.read_text(errors="replace").splitlines():
        if line.startswith(env + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _ask(prompt: str, url: str, key: str, model: str, mx: int) -> str:
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    pl = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx, "temperature": 0}
    r = requests.post(url, headers=h, json=pl, timeout=60)
    r.raise_for_status()
    j = r.json()
    return str((j.get("choices") or [{}])[0].get("message", {}).get("content") or "")


def _ask_one_provider(args) -> tuple[str, dict[str, Any]]:
    label, model, url, env, mode, mx, prompt = args
    key = _read_env(env)
    if not key:
        return label, {"status": "missing_api_key"}
    try:
        txt = _ask(prompt, url, key, model, mx)
        if label == "minimax":
            parse_result = parse_structured_json(txt)
            parsed = parse_result.data if parse_result.ok and isinstance(parse_result.data, dict) else {}
            parse_meta = parse_result.to_json_dict()
        else:
            parsed = _try_parse_json_obj(txt) or {}
            parse_meta = {"schema": "PGGArchonStructuredParse/v1", "ok": bool(parsed), "visible_chars": len(txt), "boundary": "Non-MiniMax fallback parser; parser success only."}
        if not _has_required(parsed):
            return label, {"status": "parse_failed", "visible_chars": len(txt), "preview": txt[:300], "parse": parse_meta}
        return label, {"status": "ok", "card": parsed, "visible_chars": len(txt), "parse": parse_meta}
    except Exception as e:
        return label, {"status": "error", "error": repr(e)[:200]}


def _vote_status(per_prov: dict[str, Any]) -> str:
    """Aggregate provider status views: majority vote among ok cards."""
    from collections import Counter
    votes = [str(rec.get("card", {}).get("status", "")).upper() for rec in per_prov.values() if rec.get("status") == "ok"]
    if not votes:
        return "ABSENT"
    c = Counter(votes)
    top, count = c.most_common(1)[0]
    return top if count >= 2 else votes[0]


def collect_card(
    file_path: Path,
    file_id: str,
    title: str,
    known_key_thesis: str,
    providers: list[tuple[str, str, str, str, str, int]] | None = None,
    parallel: bool = True,
) -> dict[str, Any]:
    provs = providers or _PROVIDERS
    prompt = (
        "你是 PGG Archon 审计员，仅就以下 Super-Evolution 笔记出 STRICT JSON 状态卡。\n"
        "禁止编造文件或状态。\n"
        "返回 STRICT JSON only，键必须为: id, title, key_thesis, mapped_skill, status, providers_seen\n"
        "status 取值: ABSENT | SKELETON | PARTIAL | ACTIVE\n"
        f"file_id: {file_id}\ntitle: {title}\nknown_key_thesis: {known_key_thesis}\n"
    )
    args_list = [(label, model, url, env, mode, mx, prompt) for (label, model, url, env, mode, mx) in provs]
    per_prov: dict[str, Any] = {}
    if parallel:
        with ThreadPoolExecutor(max_workers=min(5, len(provs))) as ex:
            futures = [ex.submit(_ask_one_provider, a) for a in args_list]
            for fut in as_completed(futures):
                label, rec = fut.result()
                per_prov[label] = rec
    else:
        for a in args_list:
            label, rec = _ask_one_provider(a)
            per_prov[label] = rec

    cards = [rec["card"] for rec in per_prov.values() if rec.get("status") == "ok"]
    if cards:
        agg = dict(cards[0])
        agg["providers_seen"] = sorted([label for label, rec in per_prov.items() if rec.get("status") == "ok"])
        agg["status"] = _vote_status(per_prov)
        agg["vote_count"] = len(cards)
    else:
        agg = {
            "id": file_id,
            "title": title,
            "key_thesis": known_key_thesis,
            "mapped_skill": "absent",
            "status": "ABSENT",
            "providers_seen": [],
            "vote_count": 0,
        }
    return {
        "schema": "PGGArchonSuperEvolutionCard/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file": str(file_path),
        "file_id": file_id,
        "card": agg,
        "per_provider": per_prov,
    }


def collect_many(specs: list[dict[str, str]], out_path: Path, parallel_files: bool = True) -> dict[str, Any]:
    if parallel_files:
        cards: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [
                ex.submit(collect_card, Path(s["file"]), s["file_id"], s["title"], s["known_key_thesis"])
                for s in specs
            ]
            for fut in as_completed(futures):
                cards.append(fut.result())
        cards.sort(key=lambda c: c["file_id"])
    else:
        cards = [collect_card(Path(s["file"]), s["file_id"], s["title"], s["known_key_thesis"]) for s in specs]
    summary = {
        "schema": "PGGArchonSuperEvolutionBatch/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(cards),
        "results": cards,
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
