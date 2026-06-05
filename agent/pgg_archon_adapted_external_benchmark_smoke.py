"""Run a small real adapted-external benchmark smoke for PGG Archon.

This runner fetches a tiny public GSM8K sample from the upstream open-source
repository and calls a real Hermes provider for answers. It is intentionally
small and conservative: an adapted_external smoke, not an official GSM8K score
and not an AGI benchmark pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GSM8K_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"
BOUNDARY = "Adapted external GSM8K smoke using public sample + real Hermes model call; not official GSM8K score, not L2/full AGI proof."


@dataclass(frozen=True)
class SmokeItem:
    task_id: str
    question: str
    expected: str
    raw_answer: str
    prediction: str
    passed: bool
    latency_s: float


def fetch_gsm8k_sample(limit: int) -> list[dict[str, Any]]:
    with urllib.request.urlopen(GSM8K_URL, timeout=30) as r:
        raw = r.read().decode("utf-8")
    rows = []
    for line in raw.splitlines():
        if line.strip():
            rows.append(json.loads(line))
        if len(rows) >= limit:
            break
    if len(rows) < limit:
        raise RuntimeError(f"expected {limit} rows, got {len(rows)}")
    return rows


def extract_expected(answer: str) -> str:
    m = re.search(r"####\s*([-+]?\d[\d,]*(?:\.\d+)?)", answer)
    if not m:
        raise ValueError("missing GSM8K #### answer marker")
    return m.group(1).replace(",", "")


def extract_prediction(text: str) -> str:
    # Prefer an explicit FINAL_ANSWER marker, otherwise last number.
    m = re.search(r"FINAL_ANSWER\s*[:=]\s*([-+]?\d[\d,]*(?:\.\d+)?)", text, flags=re.I)
    if m:
        return m.group(1).replace(",", "")
    nums = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", text)
    return nums[-1].replace(",", "") if nums else ""


def ask_hermes(provider: str, model: str, question: str, timeout: int) -> tuple[str, float, int, str]:
    prompt = (
        "Solve this grade-school math problem. Reply briefly and include exactly one line "
        "at the end in the form FINAL_ANSWER: <number>.\n\n" + question
    )
    t0 = time.time()
    p = subprocess.run(
        ["hermes", "-z", prompt, "--provider", f"custom:{provider}", "--model", model],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return (p.stdout or "").strip(), round(time.time() - t0, 3), p.returncode, (p.stderr or "").strip()


def run_smoke(*, provider: str, model: str, limit: int, timeout: int, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset = fetch_gsm8k_sample(limit)
    dataset_raw = "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in dataset)
    items: list[SmokeItem] = []
    raw_calls: list[dict[str, Any]] = []
    for idx, row in enumerate(dataset):
        task_id = f"gsm8k-test-{idx:03d}"
        expected = extract_expected(row["answer"])
        try:
            raw, latency, rc, stderr = ask_hermes(provider, model, row["question"], timeout)
        except subprocess.TimeoutExpired:
            raw, latency, rc, stderr = "", float(timeout), 124, "TIMEOUT"
        pred = extract_prediction(raw)
        passed = rc == 0 and pred == expected
        items.append(SmokeItem(task_id, row["question"], expected, raw, pred, passed, latency))
        raw_calls.append({"task_id": task_id, "returncode": rc, "stderr": stderr, "stdout_sha256": hashlib.sha256(raw.encode()).hexdigest(), "stdout_chars": len(raw)})
    passed_count = sum(1 for x in items if x.passed)
    run_id = datetime.now(timezone.utc).strftime("gsm8k-adapted-smoke-%Y%m%dT%H%M%SZ")
    report = {
        "schema": "PGGArchonAdaptedExternalBenchmarkSmoke/v1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "gsm8k_public_github_sample",
        "source_type": "adapted_external",
        "source_url": GSM8K_URL,
        "source_sha256": hashlib.sha256(dataset_raw.encode()).hexdigest(),
        "provider": provider,
        "model": model,
        "sample_count": len(items),
        "passed_count": passed_count,
        "accuracy": round(passed_count / len(items), 6) if items else 0.0,
        "metric": "exact_numeric_match_on_final_answer",
        "items": [asdict(x) for x in items],
        "raw_calls": raw_calls,
        "boundary": BOUNDARY,
    }
    report_path = out_dir / "adapted_gsm8k_smoke_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "WATCH",
        "run_status": "COMPLETED",
        "report_path": str(report_path),
        "accuracy": report["accuracy"],
        "sample_count": len(items),
        "passed_count": passed_count,
        "boundary": BOUNDARY,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="gpt55_5yuantoken")
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=75)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    print(json.dumps(run_smoke(provider=args.provider, model=args.model, limit=args.limit, timeout=args.timeout, out_dir=Path(args.out_dir).expanduser()), ensure_ascii=False))


if __name__ == "__main__":
    main()
