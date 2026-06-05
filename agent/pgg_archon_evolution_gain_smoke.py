"""Evidence-level evolution gain smoke for PGG Archon benchmark bridge.

This script compares a pre-smoke evidence state with a post-smoke state produced
by a real adapted external benchmark smoke report. It measures evidence-chain
completion gain, not model intelligence gain.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.pgg_archon_external_benchmark_bridge import EvolutionGainItem, compute_evolution_gain, write_json_report

BOUNDARY = "Evidence-completeness gain only; not model capability gain, not official benchmark pass, not L2/full AGI proof."


def _exists(path: str | Path) -> bool:
    return Path(path).expanduser().exists()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def evidence_score(*, bridge_report: dict, smoke_report: dict | None) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []
    src = bridge_report.get("evidence_summary", {}).get("source_types", {})
    if src.get("adapted_external", 0) >= 1:
        score += 0.25
        reasons.append("adapted_external_source_registered")
    if src.get("official_harness", 0) >= 1:
        score += 0.15
        reasons.append("official_harness_source_registered_not_run")
    if smoke_report:
        if smoke_report.get("schema") == "PGGArchonAdaptedExternalBenchmarkSmoke/v1":
            score += 0.25
            reasons.append("adapted_external_smoke_schema_present")
        if int(smoke_report.get("sample_count") or 0) > 0:
            score += 0.15
            reasons.append("sample_count_positive")
        if smoke_report.get("items") and all(str(x.get("raw_answer", "")).strip() for x in smoke_report.get("items", [])):
            score += 0.15
            reasons.append("real_model_outputs_present")
        if smoke_report.get("source_sha256"):
            score += 0.05
            reasons.append("source_hash_present")
    return round(min(score, 1.0), 6), ",".join(reasons)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge-report", required=True)
    ap.add_argument("--smoke-report", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    bridge = _load(args.bridge_report)
    smoke = _load(args.smoke_report) if _exists(args.smoke_report) else None
    before_score, before_reason = evidence_score(bridge_report=bridge, smoke_report=None)
    after_score, after_reason = evidence_score(bridge_report=bridge, smoke_report=smoke)
    item = EvolutionGainItem(
        task_id="adapted_external_benchmark_evidence_completion",
        before_status="WATCH",
        after_status="WATCH",
        before_score=before_score,
        after_score=after_score,
        evidence_path=str(Path(args.smoke_report).expanduser()),
        regression_reason="" if after_score >= before_score else "evidence score regressed",
    )
    report = compute_evolution_gain(
        baseline_label="before_adapted_external_smoke_artifact",
        evolved_label="after_real_adapted_external_smoke_artifact",
        items=[item],
    )
    out = Path(args.out).expanduser()
    write_json_report(report, out)
    payload = {
        "status": report.status,
        "out": str(out),
        "before_score": before_score,
        "after_score": after_score,
        "before_reason": before_reason,
        "after_reason": after_reason,
        "evidence_improved": bool(after_score > before_score and smoke),
        "boundary": BOUNDARY,
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
