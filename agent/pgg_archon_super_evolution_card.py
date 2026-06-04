from __future__ import annotations

import json
import re
import requests
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

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
    ("mimo", "mimo-v2.5-pro", "https://token-plan-cn.xiaomimimo.com/v1/chat/completions", "MIMO_V25_PRO_API_KEY", "chat", 4096),
    ("agnes", "agnes-2.0-flash", "https://apihub.agnes-ai.com/v1/chat/completions", "AGNES_AI_API_KEY", "chat", 2200),
    ("minimax", "MiniMax-M3", "https://api.minimax.chat/v1/chat/completions", "MINIMAX_API_KEY", "chat", 2200),
    ("gpt55", "gpt-5.5", "https://chuangagent.eu.cc/v1/chat/completions", "GPT55_5YUANTOKEN_API_KEY", "chat", 4096),
]


def _ask(prompt: str, url: str, key: str, model: str, mx: int) -> str:
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    pl = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx, "temperature": 0}
    r = requests.post(url, headers=h, json=pl, timeout=60)
    r.raise_for_status()
    j = r.json()
    return str((j.get("choices") or [{}])[0].get("message", {}).get("content") or "")


def collect_card(
    file_path: Path,
    file_id: str,
    title: str,
    known_key_thesis: str,
    providers: list[tuple[str, str, str, str, str, int]] | None = None,
) -> dict[str, Any]:
    provs = providers or _PROVIDERS
    prompt = (
        "你是 PGG Archon 审计员，仅就以下 Super-Evolution 笔记出 STRICT JSON 状态卡。\n"
        "禁止编造文件或状态。\n"
        "返回 STRICT JSON only，键必须为: id, title, key_thesis, mapped_skill, status, providers_seen\n"
        "status 取值: ABSENT | SKELETON | PARTIAL | ACTIVE\n"
        f"file_id: {file_id}\ntitle: {title}\nknown_key_thesis: {known_key_thesis}\n"
    )
    per_prov: dict[str, Any] = {}
    seen_status: list[str] = []
    for label, model, url, env, mode, mx in provs:
        key = (Path.home() / ".hermes/.env").read_text(errors="replace")
        v = ""
        for line in key.splitlines():
            if line.startswith(env + "="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
        if not v:
            per_prov[label] = {"status": "missing_api_key"}
            continue
        try:
            txt = _ask(prompt, url, v, model, mx)
            parsed = _try_parse_json_obj(txt) or {}
            if not _has_required(parsed):
                per_prov[label] = {"status": "parse_failed", "visible_chars": len(txt), "preview": txt[:300]}
                continue
            per_prov[label] = {"status": "ok", "card": parsed, "visible_chars": len(txt)}
            seen_status.append(str(parsed.get("status") or "?"))
        except Exception as e:
            per_prov[label] = {"status": "error", "error": repr(e)[:200]}

    # aggregate: take the first parseable card or fall back to local knowledge
    cards = [rec["card"] for rec in per_prov.values() if rec.get("status") == "ok"]
    if cards:
        agg = dict(cards[0])
        agg["providers_seen"] = sorted([label for label, rec in per_prov.items() if rec.get("status") == "ok"])
    else:
        agg = {
            "id": file_id,
            "title": title,
            "key_thesis": known_key_thesis,
            "mapped_skill": "absent",
            "status": "ABSENT",
            "providers_seen": [],
        }
    return {
        "schema": "PGGArchonSuperEvolutionCard/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file": str(file_path),
        "file_id": file_id,
        "card": agg,
        "per_provider": per_prov,
    }


def collect_many(specs: list[dict[str, str]], out_path: Path) -> dict[str, Any]:
    results = []
    for spec in specs:
        rec = collect_card(Path(spec["file"]), spec["file_id"], spec["title"], spec["known_key_thesis"])
        results.append(rec)
    summary = {
        "schema": "PGGArchonSuperEvolutionBatch/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "results": results,
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
