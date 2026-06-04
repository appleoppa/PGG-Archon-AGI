"""Bounded PGG Archon verifiers — extract pass/fail summaries from smoke files.

Reads the smoke JSONs under ~/.hermes/workspace/audit/p3_full_smoke_*/ and
emits a compact verifier-friendly JSON listing which provider passed
which item, with per-category refusal rate and per-benchmark accuracy.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _safe_load(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect_p3_verify_report(smoke_dir: Path) -> dict[str, Any]:
    report: dict[str, Any] = {"schema": "PGGArchonP3VerifyReport/v1", "smoke_dir": str(smoke_dir)}

    # redteam
    rt = {}
    for prov, fname in [("deepseek", "redteam_deepseek_full.json"), ("mimo", "redteam_mimo_full.json")]:
        d = _safe_load(smoke_dir / fname)
        if not d:
            continue
        verdicts = d.get("verdicts", [])
        refused = sum(1 for v in verdicts if v.get("refused") is True)
        by_cat: dict[str, dict[str, int]] = {}
        for v in verdicts:
            cat = v.get("category", "unknown")
            slot = by_cat.setdefault(cat, {"refused": 0, "total": 0})
            slot["total"] += 1
            if v.get("refused") is True:
                slot["refused"] += 1
        rt[prov] = {
            "refused": refused,
            "total": len(verdicts),
            "refusal_rate": refused / max(len(verdicts), 1),
            "by_category": by_cat,
            "errors": [v for v in verdicts if v.get("status") == "error"],
        }
    report["redteam"] = rt

    # bench
    bn = {}
    for prov, fname in [
        ("deepseek", "bench_deepseek_full.json"),
        ("mimo", "bench_mimo_full.json"),
        ("agnes", "bench_agnes_full.json"),
    ]:
        d = _safe_load(smoke_dir / fname)
        if not d:
            continue
        items = d.get("items", [])
        per_bench: dict[str, dict[str, int]] = {}
        wrong: list[dict[str, Any]] = []
        for it in items:
            bench = it.get("benchmark", "unknown")
            slot = per_bench.setdefault(bench, {"correct": 0, "total": 0})
            slot["total"] += 1
            if it.get("correct") is True:
                slot["correct"] += 1
            else:
                wrong.append({"benchmark": bench, "item_id": it.get("item_id"), "expected": it.get("expected"), "predicted": it.get("predicted")})
        bn[prov] = {
            "accuracy": d.get("accuracy"),
            "items": d.get("item_count"),
            "per_benchmark": per_bench,
            "wrong": wrong,
        }
    report["bench"] = bn

    return report


def write_p3_verify_report(smoke_dir: Path, out_path: Path) -> dict[str, Any]:
    data = collect_p3_verify_report(smoke_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--smoke-dir",
        default=str(Path.home() / ".hermes" / "workspace" / "audit" / "p3_full_smoke_20260604_203000"),
    )
    ap.add_argument(
        "--out",
        default=str(Path.home() / ".hermes" / "workspace" / "audit" / "p3_full_smoke_20260604_203000" / "verifier_friendly_report.json"),
    )
    args = ap.parse_args()
    data = write_p3_verify_report(Path(args.smoke_dir), Path(args.out))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
