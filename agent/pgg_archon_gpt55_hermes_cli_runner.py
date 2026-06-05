"""GPT-5.5 benchmark/safety runner via Hermes' official CLI path.

This intentionally does NOT call ChuangAgent with raw urllib. It shells out to
Hermes CLI so GPT55 uses the same provider/runtime adapter that the user uses in
normal Hermes sessions.

Boundary: CLI calls are slow/costly and still an internal smoke harness, not an
official external AGI benchmark.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from agent.pgg_archon_external_benchmark_provider_run import score_item
from agent.pgg_archon_safety_provider_run import classify_safety, guarded_safety_prompt

PROVIDER = "custom:gpt55_5yuantoken"
MODEL = "gpt-5.5"


def resolve_hermes_bin() -> str:
    """Resolve Hermes CLI from explicit env or PATH; do not silently use machine-specific fallbacks."""
    return os.environ.get("HERMES_BIN") or shutil.which("hermes") or ""


def _timeout_stream_to_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


@dataclass
class CliRunResult:
    id: str
    category_or_domain: str
    prompt: str
    expected: str
    provider: str
    model: str
    mode: str
    returncode: int
    visible_chars: int
    stdout_preview: str
    stderr_preview: str
    elapsed_sec: float
    scored: dict[str, Any] | None = None
    classified: dict[str, Any] | None = None


def call_hermes_cli(prompt: str, timeout: float = 180.0) -> tuple[int, str, str, float]:
    t0 = time.time()
    hermes_bin = resolve_hermes_bin()
    if not hermes_bin:
        return 127, "", "Hermes CLI not found via HERMES_BIN or PATH", round(time.time() - t0, 3)
    try:
        proc = subprocess.run(
            [hermes_bin, "-z", prompt, "--provider", PROVIDER, "--model", MODEL, "--cli"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_stream_to_text(exc.stdout)
        stderr = _timeout_stream_to_text(exc.stderr)
        return 124, stdout.strip(), (stderr.strip() + "\nTIMEOUT").strip(), round(time.time() - t0, 3)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), round(time.time() - t0, 3)


def _run_benchmark_item(item: dict[str, Any], timeout: float) -> CliRunResult:
    rc, out, err, elapsed = call_hermes_cli(str(item["prompt"]), timeout)
    sc = score_item(str(item.get("expected", "")), out)
    return CliRunResult(
        id=str(item["id"]),
        category_or_domain=str(item.get("domain", "")),
        prompt=str(item["prompt"]),
        expected=str(item.get("expected", "")),
        provider=PROVIDER,
        model=MODEL,
        mode="benchmark",
        returncode=rc,
        visible_chars=len(out),
        stdout_preview=out[:500],
        stderr_preview=err[:500],
        elapsed_sec=elapsed,
        scored=dict(sc),
    )


def _run_safety_item(item: dict[str, Any], timeout: float) -> CliRunResult:
    effective = guarded_safety_prompt(item)
    rc, out, err, elapsed = call_hermes_cli(effective, timeout)
    cls = classify_safety(str(item.get("expected_safe", "")), out, 200 if rc == 0 else 0, err)
    return CliRunResult(
        id=str(item["id"]),
        category_or_domain=str(item.get("category", "")),
        prompt=str(item["prompt"]),
        expected=str(item.get("expected_safe", "")),
        provider=PROVIDER,
        model=MODEL,
        mode="safety",
        returncode=rc,
        visible_chars=len(out),
        stdout_preview=out[:500],
        stderr_preview=err[:500],
        elapsed_sec=elapsed,
        classified=cls,
    )


def run_cli_spec(
    spec_path: str | Path,
    output_dir: str | Path,
    *,
    mode: str,
    smoke_n: int = 0,
    offset: int = 0,
    limit: int = 0,
    max_workers: int = 1,
    timeout: float = 180.0,
) -> dict[str, Any]:
    spec_path = Path(str(spec_path)).expanduser().resolve()
    out = Path(str(output_dir)).expanduser().resolve()
    raw_dir = out / "raw_responses"
    out.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(exist_ok=True)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    all_items = spec.get("items", [])
    if smoke_n > 0:
        # Backward-compatible quick smoke: first N items.
        items = all_items[:smoke_n]
        effective_offset = 0
        effective_limit = smoke_n
    else:
        effective_offset = max(offset, 0)
        sliced = all_items[effective_offset:]
        items = sliced[:limit] if limit > 0 else sliced
        effective_limit = limit if limit > 0 else len(items)
    worker = _run_benchmark_item if mode == "benchmark" else _run_safety_item
    results: list[CliRunResult] = []
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(worker, item, timeout): item for item in items}
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            (raw_dir / f"gpt55_cli__{r.id}.json").write_text(json.dumps(asdict(r), ensure_ascii=False, indent=2), encoding="utf-8")
    results.sort(key=lambda r: r.id)
    with (out / "parsed_results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    if mode == "benchmark":
        http_ok = sum(1 for r in results if r.returncode == 0)
        scored_pass = sum(1 for r in results if r.returncode == 0 and r.scored and r.scored.get("score", 0) > 0)
        summary_extra = {"http_ok": http_ok, "scored_pass": scored_pass, "pass_rate": round(scored_pass / max(http_ok, 1), 4)}
    else:
        ok = sum(1 for r in results if r.returncode == 0)
        refuse = sum(1 for r in results if r.classified and r.classified.get("classification") == "refuse")
        safe_verify = sum(1 for r in results if r.classified and r.classified.get("classification") == "safe_verify")
        unsafe = sum(1 for r in results if r.classified and r.classified.get("classification") == "unsafe")
        summary_extra = {"http_ok": ok, "refuse": refuse, "safe_verify": safe_verify, "unsafe": unsafe, "safe_or_refusal_rate": round((refuse + safe_verify) / max(ok, 1), 4), "unsafe_rate": round(unsafe / max(ok, 1), 4)}
    summary = {
        "schema": "PGGArchonGPT55HermesCliRunner/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "spec_path": str(spec_path),
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "item_count": len(items),
        "total_spec_items": len(all_items),
        "smoke_n": smoke_n,
        "offset": effective_offset,
        "limit": effective_limit,
        "provider": PROVIDER,
        "model": MODEL,
        "hermes_bin": resolve_hermes_bin(),
        "max_workers": max_workers,
        "total_elapsed_sec": round(time.time() - t0, 2),
        **summary_extra,
        "boundary": "Uses Hermes CLI official provider path; internal smoke only, not official external AGI benchmark.",
    }
    (out / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--mode", choices=["benchmark", "safety"], required=True)
    ap.add_argument("--smoke-n", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-workers", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args(list(argv) if argv is not None else None)
    summary = run_cli_spec(
        args.spec,
        args.output_dir,
        mode=args.mode,
        smoke_n=args.smoke_n,
        offset=args.offset,
        limit=args.limit,
        max_workers=args.max_workers,
        timeout=args.timeout,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
