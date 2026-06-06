"""Semi-external legal taskset provider runner.

Runs the 100-item legal taskset derived from real case patterns through real
providers and scores process/legal-safety signals. This is NOT LegalBench and
not proof of legal correctness.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from agent.pgg_archon_external_benchmark_provider_run import PROVIDERS, _load_env, call_provider
from agent.pgg_archon_legal_task_gate import build_legal_task_prompt, score_legal_task

THIRD_PARTY_JUDGE_PROVIDER_ALIASES = {"mimo", "mimo_v25_pro_auditor", "custom:mimo_v25_pro_auditor"}
DEFAULT_ORDINARY_LEGAL_PROVIDERS = ("deepseek", "gpt55")
MAX_LEGAL_TASK_TIMEOUT_SEC = 90.0
MAX_LEGAL_TASK_WORKERS = 5

LEGAL_RUNNER_BOUNDARY = (
    "Bounded semi-external legal taskset process-safety smoke only; not official "
    "LegalBench/LexGLUE, not legal correctness proof, not external-delivery approval. "
    "MiMo is reserved for third-party judging and is blocked from ordinary processing pools."
)


def _is_third_party_judge_provider(name: str) -> bool:
    return (name or "").strip().lower() in THIRD_PARTY_JUDGE_PROVIDER_ALIASES


def _clamp_timeout(timeout: float) -> float:
    try:
        value = float(timeout)
    except (TypeError, ValueError):
        value = MAX_LEGAL_TASK_TIMEOUT_SEC
    return min(max(value, 1.0), MAX_LEGAL_TASK_TIMEOUT_SEC)


def _clamp_workers(max_workers: int) -> int:
    try:
        value = int(max_workers)
    except (TypeError, ValueError):
        value = MAX_LEGAL_TASK_WORKERS
    return min(max(value, 1), MAX_LEGAL_TASK_WORKERS)


def _select_ordinary_providers(requested: list[str] | None = None) -> tuple[list[Any], list[str]]:
    requested_set = None
    blocked: list[str] = []
    if requested is not None:
        requested_set = {x.strip() for x in requested if x and x.strip()}
        blocked = sorted(x for x in requested_set if _is_third_party_judge_provider(x))
        if blocked:
            raise ValueError(f"MiMo is a third-party judge and cannot be used as ordinary legal runner provider: {blocked}")
    defaults = set(DEFAULT_ORDINARY_LEGAL_PROVIDERS)
    selected = []
    for p in PROVIDERS:
        if _is_third_party_judge_provider(getattr(p, "name", "")):
            blocked.append(getattr(p, "name", ""))
            continue
        if requested_set is None:
            if getattr(p, "name", "") in defaults:
                selected.append(p)
        elif getattr(p, "name", "") in requested_set:
            selected.append(p)
    return selected, sorted(set(blocked))


def score_legal_item(expected: str, text: str, *, domain: str = "") -> dict[str, Any]:
    """Backward-compatible wrapper around the core legal task gate."""
    return score_legal_task(expected, text, domain=domain)


def run_one(provider: Any, item: dict[str, Any], timeout: float) -> dict[str, Any]:
    prompt = build_legal_task_prompt(item)
    resp = call_provider(provider, prompt, timeout)
    text = resp.get("parsed_text", "") or ""
    scored = score_legal_item(str(item.get("expected", "")), text, domain=str(item.get("domain", "")))
    return {
        "id": item["id"],
        "domain": item["domain"],
        "scenario": item.get("scenario", ""),
        "expected": item.get("expected", ""),
        "provider": provider.name,
        "model": resp.get("model", provider.model),
        "api_mode": resp.get("api_mode", provider.api_mode),
        "http_status": resp.get("http_status", 0),
        "visible_chars": len(text),
        "parsed_text_preview": text[:500],
        "raw_body": resp.get("raw_body", ""),
        "elapsed_sec": resp.get("elapsed_sec", 0.0),
        "error": resp.get("error", ""),
        "scored": scored,
    }


def run_taskset(
    spec_path: str | Path,
    output_dir: str | Path,
    *,
    providers: list[str] | None = None,
    smoke_n: int = 0,
    max_workers: int = MAX_LEGAL_TASK_WORKERS,
    timeout: float = MAX_LEGAL_TASK_TIMEOUT_SEC,
) -> dict[str, Any]:
    timeout = _clamp_timeout(timeout)
    max_workers = _clamp_workers(max_workers)
    spec_path = Path(str(spec_path)).expanduser().resolve()
    out = Path(str(output_dir)).expanduser().resolve()
    raw_dir = out / "raw_responses"
    out.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(exist_ok=True)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    items = spec.get("items", [])[:smoke_n] if smoke_n > 0 else spec.get("items", [])
    selected, blocked_providers = _select_ordinary_providers(providers)
    tasks = [(p, it) for p in selected for it in items]
    results: list[dict[str, Any]] = []
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        log_lines.append(line)

    log(f"loaded items={len(items)} providers={[p.name for p in selected]} out={out}")
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_one, p, it, timeout): (p, it) for p, it in tasks}
        done = 0
        for fut in cf.as_completed(futs):
            p, it = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"id": it["id"], "domain": it["domain"], "scenario": it.get("scenario", ""), "expected": it.get("expected", ""), "provider": p.name, "model": p.model, "api_mode": p.api_mode, "http_status": 0, "visible_chars": 0, "parsed_text_preview": "", "raw_body": "", "elapsed_sec": 0.0, "error": f"executor error: {type(e).__name__}: {e}", "scored": {"score": 0.0, "reason": "executor_error", "matched": []}}
            results.append(r)
            (raw_dir / f"{r['provider']}__{r['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            done += 1
            if done % 25 == 0 or done == len(tasks):
                ok = sum(1 for x in results if x.get("http_status") == 200)
                passed = sum(1 for x in results if x.get("http_status") == 200 and x.get("scored", {}).get("score", 0) > 0)
                log(f"progress {done}/{len(tasks)} http_ok={ok} scored_pass={passed} elapsed={time.time()-t0:.1f}s")
    results.sort(key=lambda r: (r["provider"], r["id"]))
    with (out / "parsed_results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_domain: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        by_provider[r["provider"]].append(r)
        by_domain[r["domain"]][r["provider"]].append(r)
    per_provider = {}
    for p, rs in sorted(by_provider.items()):
        ok = sum(1 for x in rs if x.get("http_status") == 200)
        passed = sum(1 for x in rs if x.get("http_status") == 200 and x.get("scored", {}).get("score", 0) > 0)
        per_provider[p] = {"items_total": len(rs), "http_ok": ok, "scored_pass": passed, "pass_rate": round(passed / max(len(rs), 1), 4), "http_ok_rate": round(ok / max(len(rs), 1), 4), "avg_visible_chars": round(sum(x.get("visible_chars", 0) for x in rs) / max(len(rs), 1), 1), "error_count": sum(1 for x in rs if x.get("error"))}
    per_domain = {}
    for d, provs in sorted(by_domain.items()):
        per_domain[d] = {}
        for p, rs in sorted(provs.items()):
            ok = sum(1 for x in rs if x.get("http_status") == 200)
            passed = sum(1 for x in rs if x.get("http_status") == 200 and x.get("scored", {}).get("score", 0) > 0)
            per_domain[d][p] = {"items": len(rs), "http_ok": ok, "scored_pass": passed, "pass_rate": round(passed / max(len(rs), 1), 4), "http_ok_rate": round(ok / max(len(rs), 1), 4)}
    summary = {
        "schema": "PGGSemiExternalLegalTasksetProviderRun/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec_path": str(spec_path),
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "item_count": len(items),
        "provider_count": len(selected),
        "providers_completed": [p.name for p in selected],
        "blocked_third_party_judge_providers": blocked_providers,
        "timeout_sec": timeout,
        "max_workers": max_workers,
        "per_provider": per_provider,
        "per_domain": per_domain,
        "total_elapsed_sec": round(time.time() - t0, 2),
        "boundary": LEGAL_RUNNER_BOUNDARY,
    }
    (out / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "run_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--providers", default=",".join(DEFAULT_ORDINARY_LEGAL_PROVIDERS))
    ap.add_argument("--smoke-n", type=int, default=0)
    ap.add_argument("--max-workers", type=int, default=MAX_LEGAL_TASK_WORKERS)
    ap.add_argument("--timeout", type=float, default=MAX_LEGAL_TASK_TIMEOUT_SEC)
    ap.add_argument("--env-path", default=str(Path.home() / ".hermes" / ".env"))
    args = ap.parse_args(list(argv) if argv is not None else None)
    _load_env(args.env_path)
    providers = [x.strip() for x in args.providers.split(",") if x.strip()]
    summary = run_taskset(args.spec, args.output_dir, providers=providers, smoke_n=args.smoke_n, max_workers=args.max_workers, timeout=args.timeout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
