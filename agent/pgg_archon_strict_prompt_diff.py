"""Bounded PGG Archon strict-prompt redteam diff — measure refusal-rate delta when 7 weak-category prompts are tightened.

Compares v0 (loose prompts) vs v1 (strict prompts) on the same 50-probe
corpus + same provider (DeepSeek) + same heuristic.

Output: per-category delta + corpus-wide refusal_rate delta.

This module does NOT re-run the harness; it only reads the two smoke
JSONs and emits a verifier-friendly diff. Real benchmark numbers
depend on real runs.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def _per_category(verdicts: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    c: dict[str, dict[str, int]] = {}
    for v in verdicts:
        cat = v.get("category", "?")
        slot = c.setdefault(cat, {"refused": 0, "total": 0})
        slot["total"] += 1
        if v.get("refused") is True:
            slot["refused"] += 1
    return c


def diff_p3_50(v0_path: Path, v1_path: Path) -> dict[str, Any]:
    v0 = json.loads(v0_path.read_text(encoding="utf-8"))
    v1 = json.loads(v1_path.read_text(encoding="utf-8"))
    v0c = _per_category(v0["verdicts"])
    v1c = _per_category(v1["verdicts"])
    all_cats = sorted(set(v0c.keys()) | set(v1c.keys()))
    rows = []
    for cat in all_cats:
        v0s = v0c.get(cat, {"refused": 0, "total": 0})
        v1s = v1c.get(cat, {"refused": 0, "total": 0})
        v0_rate = v0s["refused"] / max(v0s["total"], 1)
        v1_rate = v1s["refused"] / max(v1s["total"], 1)
        rows.append({
            "category": cat,
            "v0_refused": v0s["refused"],
            "v0_total": v0s["total"],
            "v0_rate": round(v0_rate, 3),
            "v1_refused": v1s["refused"],
            "v1_total": v1s["total"],
            "v1_rate": round(v1_rate, 3),
            "delta_rate": round(v1_rate - v0_rate, 3),
        })
    v0r = sum(s["refused"] for s in v0c.values())
    v0t = sum(s["total"] for s in v0c.values())
    v1r = sum(s["refused"] for s in v1c.values())
    v1t = sum(s["total"] for s in v1c.values())
    return {
        "schema": "PGGArchonP3StrictPromptDiff/v1",
        "per_category": rows,
        "v0_overall": {"refused": v0r, "total": v0t, "rate": round(v0r / max(v0t, 1), 3)},
        "v1_overall": {"refused": v1r, "total": v1t, "rate": round(v1r / max(v1t, 1), 3)},
        "delta_overall_rate": round((v1r / max(v1t, 1)) - (v0r / max(v0t, 1)), 3),
        "boundary": "compares two 50-probe DeepSeek smoke runs; refusal heuristic is conservative",
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--v0", required=True)
    ap.add_argument("--v1", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    summary = diff_p3_50(Path(args.v0), Path(args.v1))
    Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"v0": summary["v0_overall"], "v1": summary["v1_overall"], "delta_rate": summary["delta_overall_rate"]}, ensure_ascii=False, indent=2))
