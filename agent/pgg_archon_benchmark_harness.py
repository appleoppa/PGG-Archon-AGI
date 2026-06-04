"""Bounded PGG Archon benchmark runner + reporter.

For each configured provider, run the loader on every supported benchmark
(mmlu, gsm8k, bigbench) and emit a per-item verdict JSON. The runner is
deterministic, low-cost, and uses chat_completions with max_tokens=64.

Boundary: this harness is a *status surface*. The 5-item corpus is too
small to claim a real MMLU/GSM8K/BigBench score; it can only demonstrate
that the harness is wired and the provider is reachable.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pgg_archon_benchmark_corpus import BenchItem, list_benchmarks, load_benchmark


@dataclass
class ItemVerdict:
    benchmark: str
    item_id: str
    question: str
    expected: str
    predicted: str
    correct: bool
    http_status: int | None = None
    visible_chars: int = 0
    note: str = ""


@dataclass
class BenchReport:
    provider: str
    model: str
    started_at: str
    finished_at: str
    items: list[ItemVerdict] = field(default_factory=list)

    def accuracy(self) -> float:
        if not self.items:
            return 0.0
        return sum(1 for i in self.items if i.correct) / len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "PGGArchonBenchReport/v1",
            "provider": self.provider,
            "model": self.model,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "item_count": len(self.items),
            "accuracy": self.accuracy(),
            "items": [asdict(i) for i in self.items],
            "boundary": "5-item status corpus only; not a real MMLU/GSM8K/BigBench score",
        }


def _run_item(provider_url: str, model: str, api_key: str, bench_name: str, item: BenchItem, timeout: int = 60) -> ItemVerdict:
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": f"Q: {item.question}\nA (short):"}],
        "max_tokens": 64,
        "temperature": 0,
    }
    try:
        r = requests.post(provider_url, headers=headers, json=payload, timeout=timeout)
        if r.status_code >= 400:
            return ItemVerdict(
                benchmark=bench_name, item_id=item.id, question=item.question,
                expected=item.answer, predicted="", correct=False,
                http_status=r.status_code, note=f"http_{r.status_code}",
            )
        data = r.json()
        text = str((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
        # Loose correctness: expected substring appears in predicted
        ok = item.answer.lower() in text.lower()
        return ItemVerdict(
            benchmark=bench_name, item_id=item.id, question=item.question,
            expected=item.answer, predicted=text[:200], correct=ok,
            http_status=200, visible_chars=len(text),
        )
    except Exception as e:
        return ItemVerdict(
            benchmark=bench_name, item_id=item.id, question=item.question,
            expected=item.answer, predicted="", correct=False, note=repr(e)[:120],
        )


def run_bench(provider_name: str, model: str, base_url: str, api_key: str, benchmarks: list[str] | None = None, timeout: int = 60) -> BenchReport:
    started = datetime.now(timezone.utc).isoformat()
    url = base_url.rstrip("/") + "/chat/completions"
    targets = benchmarks or list_benchmarks()
    items: list[ItemVerdict] = []
    for name in targets:
        for it in load_benchmark(name):
            items.append(_run_item(url, model, api_key, name, it, timeout=timeout))
    return BenchReport(
        provider=provider_name, model=model,
        started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )


def write_bench_report(report: BenchReport, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = report.to_dict()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--api-key-env", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bench", nargs="*", default=None)
    args = ap.parse_args()
    key = os.environ.get(args.api_key_env, "")
    if not key:
        print(f"ERROR  missing env {args.api_key_env}")
        return 1
    rep = run_bench(args.provider, args.model, args.base_url, key, benchmarks=args.bench)
    data = write_bench_report(rep, Path(args.out))
    print(json.dumps({"accuracy": data["accuracy"], "items": data["item_count"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
