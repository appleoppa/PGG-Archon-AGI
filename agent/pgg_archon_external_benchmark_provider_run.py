"""PGG Archon external benchmark provider-run.

Real LLM-backed runner for the 100-item frozen external benchmark smoke.
Calls DeepSeek, MiMo, and gpt5.5 in parallel, saves raw responses,
visible chars, parsed answer, deterministic score per item.

Boundary:
- 100-item frozen internal smoke spec; not official MMLU/GSM8K/BigBench/LegalBench score.
- 3 providers (DeepSeek/MiMo/gpt5.5), claude excluded by user direction.
- gpt5.5 uses Responses API (codex_responses) per config.yaml.
- MiniMax not in primary P0; per handoff it would be a structured-adapter verifier.

Outputs (to --output-dir):
  - raw_responses/<provider>__<bench-id>.json
  - parsed_results.jsonl  (one line per provider×item)
  - run_summary.json  (per_provider pass_rate, per_domain pass_rate, totals)
  - provider_run_log.txt
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

# --- .env loader (launchd plist env not visible in plain shell) ---
def _load_env(env_path: str | Path) -> int:
    p = Path(env_path).expanduser()
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)
        n += 1
    return n


# --- Provider registry (verified 2026-06-05 from ~/.hermes/config.yaml + .env) ---
# Each provider carries a runtime `healthy` flag set by probe_provider().
# Providers that fail the health probe are downgraded to ERROR/UNKNOWN for that run
# (per user policy: "single-channel failure must not block overall progress; mark
# ERROR/UNKNOWN, do not fake PASS").
class ProviderSpec:
    __slots__ = ("name", "api_mode", "base_url", "chat_path", "responses_path",
                 "model", "key_env", "max_tokens", "healthy", "probe_note")
    def __init__(self, name: str, api_mode: str, base_url: str, chat_path: str,
                 responses_path: str, model: str, key_env: str, max_tokens: int):
        self.name = name
        self.api_mode = api_mode
        self.base_url = base_url
        self.chat_path = chat_path
        self.responses_path = responses_path
        self.model = model
        self.key_env = key_env
        self.max_tokens = max_tokens
        self.healthy = True
        self.probe_note = ""

    def __repr__(self) -> str:
        return f"ProviderSpec({self.name}, healthy={self.healthy}, note={self.probe_note!r})"


PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="deepseek",
        api_mode="chat",
        base_url="https://api.deepseek.com",
        chat_path="/v1/chat/completions",
        responses_path="",
        model="deepseek-v4-flash",
        key_env="DEEPSEEK_V4_FLASH_API_KEY",
        max_tokens=4096,  # reasoning model
    ),
    ProviderSpec(
        name="mimo",
        api_mode="chat",
        base_url="https://token-plan-cn.xiaomimimo.com",
        chat_path="/v1/chat/completions",
        responses_path="",
        model="mimo-v2.5-pro",
        key_env="MIMO_V25_PRO_API_KEY",
        max_tokens=4096,  # reasoning model
    ),
    ProviderSpec(
        name="gpt55",
        api_mode="codex_responses",
        base_url="https://chuangagent.eu.cc",
        chat_path="",
        responses_path="/v1/responses",
        model="gpt-5.5",
        key_env="GPT55_5YUANTOKEN_API_KEY",
        max_tokens=4096,
    ),
]


# --- HTTP call ---
def _http_post_json(url: str, headers: dict[str, str], body: dict[str, Any], timeout: float) -> tuple[int, str]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = f"<HTTPError {e.code} without body>"
        return e.code, raw
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, f"<network error: {type(e).__name__}: {e}>"


def call_provider(spec: ProviderSpec, prompt: str, timeout: float) -> dict[str, Any]:
    """Single LLM call. Returns dict with http_status, raw_body, parsed_text, error."""
    api_key = os.environ.get(spec.key_env, "")
    t0 = time.time()
    if not api_key:
        return {
            "provider": spec.name,
            "model": spec.model,
            "api_mode": spec.api_mode,
            "http_status": 0,
            "raw_body": "",
            "parsed_text": "",
            "elapsed_sec": 0.0,
            "error": f"missing api key env {spec.key_env}",
        }
    if spec.api_mode == "chat":
        url = spec.base_url.rstrip("/") + spec.chat_path
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        body = {
            "model": spec.model,
            "messages": [
                {"role": "system", "content": "You are a precise short-answer assistant. Reply concisely. If a tool or code is required, say so. Do not hedge on yes/no questions."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": spec.max_tokens,
            "temperature": 0.0,
        }
        status, raw = _http_post_json(url, headers, body, timeout)
        parsed = ""
        if status == 200 and raw:
            try:
                obj = json.loads(raw)
                parsed = obj["choices"][0]["message"].get("content", "") or ""
            except Exception as e:
                raw = raw + f"\n<json parse error: {e}>"
        return {
            "provider": spec.name,
            "model": spec.model,
            "api_mode": spec.api_mode,
            "http_status": status,
            "raw_body": raw,
            "parsed_text": parsed,
            "elapsed_sec": round(time.time() - t0, 3),
            "error": "" if status == 200 else f"http_status={status}",
        }
    elif spec.api_mode == "codex_responses":
        url = spec.base_url.rstrip("/") + spec.responses_path
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        body = {
            "model": spec.model,
            "input": [
                {"role": "system", "content": "You are a precise short-answer assistant. Reply concisely. If a tool or code is required, say so. Do not hedge on yes/no questions."},
                {"role": "user", "content": prompt},
            ],
            # chuangagent.eu.cc gpt-5.5 quirk: max_output_tokens may be ignored
            # and reasoning eats the whole budget. Use max_tokens (chat-style) and
            # also set a high max_output_tokens for Responses API.
            "max_tokens": spec.max_tokens,
            "max_output_tokens": spec.max_tokens,
        }
        status, raw = _http_post_json(url, headers, body, timeout)
        parsed = ""
        if status == 200 and raw:
            try:
                obj = json.loads(raw)
                # Responses API: extract text from output[].content[].text
                for item in obj.get("output", []) or []:
                    for c in item.get("content", []) or []:
                        if c.get("type") in ("output_text", "text"):
                            parsed += c.get("text", "")
                if not parsed:
                    # fall back: try older shapes
                    if "choices" in obj:
                        parsed = obj["choices"][0].get("message", {}).get("content", "") or ""
                    if not parsed:
                        raw = raw + "\n<no text extracted from output[]>"
            except Exception as e:
                raw = raw + f"\n<json parse error: {e}>"
        return {
            "provider": spec.name,
            "model": spec.model,
            "api_mode": spec.api_mode,
            "http_status": status,
            "raw_body": raw,
            "parsed_text": parsed,
            "elapsed_sec": round(time.time() - t0, 3),
            "error": "" if status == 200 else f"http_status={status}",
        }
    else:
        return {
            "provider": spec.name,
            "model": spec.model,
            "api_mode": spec.api_mode,
            "http_status": 0,
            "raw_body": "",
            "parsed_text": "",
            "elapsed_sec": 0.0,
            "error": f"unknown api_mode={spec.api_mode}",
        }


# --- Deterministic scorer for the 100 frozen items ---
YES_TOKENS = ["yes", "是", "对", "correct", "true", "affirm"]
NO_TOKENS = ["no", "不", "否", "false", "negative", "not"]
CALC_TOKENS = ["calculator", "code", "python", "execute", "calculation tool", "tool", "compute", "shell"]
EVIDENCE_TOKENS = ["evidence", "summarize", "summarise", "first", "before conclusion", "evidence first", "review evidence"]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def score_item(expected: str, text: str) -> dict[str, Any]:
    """Deterministic substring/keyword match against the 4 expected buckets."""
    n = _norm(text)
    if not n:
        return {"expected": expected, "parsed_norm": "", "matched": None, "score": 0.0, "reason": "empty"}
    if expected == "yes":
        hit = any(tok in n for tok in YES_TOKENS) and not any(tok in n for tok in NO_TOKENS)
        return {"expected": expected, "parsed_norm": n[:120], "matched": "yes" if hit else None, "score": 1.0 if hit else 0.0,
                "reason": "yes-keyword" if hit else "no yes-keyword"}
    if expected == "no":
        hit = any(tok in n for tok in NO_TOKENS) and not any(tok in n for tok in YES_TOKENS)
        return {"expected": expected, "parsed_norm": n[:120], "matched": "no" if hit else None, "score": 1.0 if hit else 0.0,
                "reason": "no-keyword" if hit else "no no-keyword"}
    if expected == "calculator_or_code":
        hit = any(tok in n for tok in CALC_TOKENS)
        return {"expected": expected, "parsed_norm": n[:120], "matched": "calculator_or_code" if hit else None, "score": 1.0 if hit else 0.0,
                "reason": "calc-keyword" if hit else "no calc-keyword"}
    if expected == "evidence_first":
        hit = any(tok in n for tok in EVIDENCE_TOKENS)
        return {"expected": expected, "parsed_norm": n[:120], "matched": "evidence_first" if hit else None, "score": 1.0 if hit else 0.0,
                "reason": "evidence-keyword" if hit else "no evidence-keyword"}
    return {"expected": expected, "parsed_norm": n[:120], "matched": None, "score": 0.0, "reason": f"unknown expected={expected}"}


# --- Per-item worker ---
def run_one(spec: ProviderSpec, item: dict[str, Any], timeout: float) -> dict[str, Any]:
    resp = call_provider(spec, item["prompt"], timeout)
    visible_chars = len(resp.get("parsed_text", ""))
    sc = score_item(item["expected"], resp.get("parsed_text", ""))
    return {
        "id": item["id"],
        "domain": item["domain"],
        "prompt": item["prompt"],
        "expected": item["expected"],
        "provider": spec.name,
        "model": resp.get("model", spec.model),
        "api_mode": resp.get("api_mode", spec.api_mode),
        "http_status": resp.get("http_status", 0),
        "visible_chars": visible_chars,
        "parsed_text_preview": (resp.get("parsed_text", "") or "")[:200],
        "raw_body": resp.get("raw_body", ""),
        "elapsed_sec": resp.get("elapsed_sec", 0.0),
        "error": resp.get("error", ""),
        "scored": sc,
    }


def probe_provider(spec: ProviderSpec, probe_item: dict[str, Any], timeout: float) -> dict[str, Any]:
    """One-shot health probe. Marks spec.healthy=True iff HTTP 200 AND visible_chars>0."""
    r = call_provider(spec, probe_item["prompt"], timeout)
    http_ok = r.get("http_status") == 200
    has_text = len(r.get("parsed_text", "")) > 0
    spec.healthy = bool(http_ok and has_text)
    spec.probe_note = f"http={r.get('http_status')} chars={len(r.get('parsed_text',''))} err={r.get('error','')}"
    return {
        "provider": spec.name,
        "healthy": spec.healthy,
        "probe_note": spec.probe_note,
        "probe_http": r.get("http_status"),
        "probe_chars": len(r.get("parsed_text", "")),
        "probe_error": r.get("error", ""),
        "probe_parsed_preview": (r.get("parsed_text", "") or "")[:160],
        "probe_raw": r.get("raw_body", "")[:400],
    }


# --- Main run ---
def run_benchmark(spec_path: str | Path, output_dir: str | Path, max_workers: int, timeout: float, smoke_n: int) -> dict[str, Any]:
    spec_path = Path(str(spec_path)).expanduser().resolve()
    output_dir = Path(str(output_dir)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw_responses"
    raw_dir.mkdir(exist_ok=True)
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        log_lines.append(line)

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    items_all = spec["items"]
    items = items_all[:smoke_n] if smoke_n > 0 else items_all
    log(f"loaded {len(items)} items (smoke_n={smoke_n}) from {spec_path}")
    log(f"output_dir={output_dir}")
    log(f"providers: {[p.name for p in PROVIDERS]}")
    log(f"max_workers={max_workers} timeout={timeout}s")

    # Health-probe every provider first (single yes/no question item).
    probe_results: list[dict[str, Any]] = []
    for sp in PROVIDERS:
        probe_item = next((i for i in items if i.get("domain") == "logic"), items[0])
        pr = probe_provider(sp, probe_item, timeout)
        probe_results.append(pr)
        log(f"probe {sp.name}: healthy={pr['healthy']} {pr['probe_note']}")

    # Build task list: skip providers that failed probe (mark them ERROR/UNKNOWN per policy).
    tasks: list[tuple[ProviderSpec, dict[str, Any]]] = []
    skipped: list[dict[str, Any]] = []
    for sp in PROVIDERS:
        if not sp.healthy:
            for it in items:
                skipped.append({"provider": sp.name, "id": it["id"], "domain": it["domain"],
                                "expected": it["expected"], "reason": f"probe_unhealthy: {sp.probe_note}"})
            continue
        for it in items:
            tasks.append((sp, it))
    log(f"total tasks: {len(tasks)} (skipped={len(skipped)} from unhealthy providers)")

    results: list[dict[str, Any]] = []
    t_run0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_one, sp, it, timeout): (sp, it) for (sp, it) in tasks}
        done = 0
        for fut in cf.as_completed(futs):
            sp, it = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"id": it["id"], "domain": it["domain"], "expected": it["expected"],
                     "provider": sp.name, "model": sp.model, "api_mode": sp.api_mode,
                     "http_status": 0, "visible_chars": 0, "parsed_text_preview": "",
                     "raw_body": "", "elapsed_sec": 0.0,
                     "error": f"executor error: {type(e).__name__}: {e}",
                     "scored": {"expected": it["expected"], "matched": None, "score": 0.0, "reason": "executor_error"}}
            results.append(r)
            # persist raw
            raw_path = raw_dir / f"{r['provider']}__{r['id']}.json"
            try:
                raw_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                log(f"warn: failed to write {raw_path}: {e}")
            done += 1
            if done % 25 == 0 or done == len(tasks):
                ok = sum(1 for x in results if x["http_status"] == 200)
                scored = sum(1 for x in results if x.get("scored", {}).get("score", 0) > 0)
                log(f"progress {done}/{len(tasks)} http_ok={ok} scored_pass={scored} elapsed={time.time()-t_run0:.1f}s")

    # Sort for determinism: by provider, then id
    results.sort(key=lambda r: (r["provider"], r["id"]))

    # Persist parsed_results.jsonl
    with (output_dir / "parsed_results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Aggregate
    by_provider: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_provider.setdefault(r["provider"], []).append(r)
    per_provider = {}
    for p, rs in by_provider.items():
        http_ok = sum(1 for x in rs if x["http_status"] == 200)
        scored = [x for x in rs if x["http_status"] == 200 and x.get("scored", {}).get("score", 0) > 0]
        per_provider[p] = {
            "model": rs[0]["model"] if rs else "",
            "api_mode": rs[0]["api_mode"] if rs else "",
            "items_total": len(rs),
            "http_ok": http_ok,
            "scored_pass": len(scored),
            "pass_rate": round(len(scored) / max(http_ok, 1), 4),
            "avg_visible_chars": round(sum(x["visible_chars"] for x in rs) / max(len(rs), 1), 1),
            "avg_elapsed_sec": round(sum(x["elapsed_sec"] for x in rs) / max(len(rs), 1), 3),
            "error_count": sum(1 for x in rs if x.get("error")),
        }
    # Per-domain pass (over http_ok only)
    domains = sorted({r["domain"] for r in results})
    per_domain: dict[str, dict[str, Any]] = {}
    for d in domains:
        per_domain[d] = {}
        for p in by_provider:
            drs = [x for x in by_provider[p] if x["domain"] == d]
            ok = sum(1 for x in drs if x["http_status"] == 200)
            sc = sum(1 for x in drs if x["http_status"] == 200 and x.get("scored", {}).get("score", 0) > 0)
            per_domain[d][p] = {
                "items": len(drs),
                "http_ok": ok,
                "scored_pass": sc,
                "pass_rate": round(sc / max(ok, 1), 4),
            }
    summary = {
        "schema": "PGGArchonExternalBenchmarkProviderRun/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec_path": str(spec_path),
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "item_count": len(items),
        "provider_count": len(PROVIDERS),
        "providers_used": [p.name for p in PROVIDERS],
        "provider_health": probe_results,
        "skipped_unhealthy": skipped,
        "per_provider": per_provider,
        "per_domain": per_domain,
        "total_elapsed_sec": round(time.time() - t_run0, 2),
        "boundary": "Real provider runs on 100-item frozen internal smoke; not MMLU/GSM8K/BigBench/LegalBench. Claude excluded; MiniMax not in P0.",
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "provider_run_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    log(f"DONE. summary written to {output_dir}/run_summary.json")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--smoke-n", type=int, default=0, help="if >0, only run first N items (smoke)")
    parser.add_argument("--env-path", default=str(Path.home() / ".hermes" / ".env"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    n = _load_env(args.env_path)
    print(f"[env] loaded {n} entries from {args.env_path}", flush=True)
    summary = run_benchmark(args.spec, args.output_dir, args.max_workers, args.timeout, args.smoke_n)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
