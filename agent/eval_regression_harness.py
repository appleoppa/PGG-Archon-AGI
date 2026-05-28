"""Evaluation regression harness for PGG Archon capability signals.

The harness converts structured metric/driver outputs into deterministic eval
cases. It is inspired by eval-driven iteration, but remains local and read-only:
it does not call models, mutate the gene database, patch code, or claim AGI
completion.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_EVAL_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/eval-regression-harness")


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _metric_items(summary: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    metrics = summary.get("metrics")
    if isinstance(metrics, Mapping):
        return [m for m in metrics.values() if isinstance(m, Mapping)]
    if isinstance(metrics, list):
        return [m for m in metrics if isinstance(m, Mapping)]
    return []


def _build_case(case_id: str, name: str, expected: Any, actual: Any, severity: str, failure_hint: str) -> dict[str, Any]:
    passed = actual == expected
    return {
        "case_id": case_id,
        "name": name,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "severity": severity,
        "failure_hint": None if passed else failure_hint,
    }


def build_eval_regression_harness(
    metrics_summary: Mapping[str, Any] | None = None,
    metric_driver: Mapping[str, Any] | None = None,
    *,
    min_known_metric_count: int = 9,
    max_p0_alerts: int = 0,
    require_driver_candidate_for_alert: bool = True,
    custom_cases: Sequence[Mapping[str, Any]] | None = None,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_EVAL_DIR,
) -> dict[str, Any]:
    """Build a deterministic regression eval report from structured signals."""
    metrics_summary = dict(metrics_summary or {})
    metric_driver = dict(metric_driver or {})
    cases: list[dict[str, Any]] = []

    metric_items = _metric_items(metrics_summary)
    known_metric_count = len([m for m in metric_items if m.get("status") not in {None, "UNKNOWN"}])
    if metrics_summary:
        cases.append(
            _build_case(
                "metrics_known_count_floor",
                "known metric count reaches floor",
                True,
                known_metric_count >= min_known_metric_count,
                "P1",
                "collect_more_capability_metric_evidence",
            )
        )
        cases.append(
            _build_case(
                "metrics_no_agi_completion_claim",
                "metrics summary must not claim AGI completion",
                False,
                bool(metrics_summary.get("agi_completion_claim")),
                "P0",
                "remove_agi_completion_claim_from_metrics",
            )
        )

    alerts = [dict(item) for item in _as_sequence(metric_driver.get("alerts")) if isinstance(item, Mapping)]
    candidates = [dict(item) for item in _as_sequence(metric_driver.get("repair_candidates")) if isinstance(item, Mapping)]
    if metric_driver:
        p0_count = len([a for a in alerts if a.get("severity") == "P0"])
        cases.append(
            _build_case(
                "metric_driver_p0_alert_budget",
                "P0 metric alerts remain within budget",
                True,
                p0_count <= max_p0_alerts,
                "P0",
                "generate_or_verify_repair_candidates_for_p0_alerts",
            )
        )
        cases.append(
            _build_case(
                "metric_driver_no_agi_completion_claim",
                "metric driver must not claim AGI completion",
                False,
                bool(metric_driver.get("agi_completion_claim")),
                "P0",
                "remove_agi_completion_claim_from_metric_driver",
            )
        )
        if require_driver_candidate_for_alert:
            cases.append(
                _build_case(
                    "metric_driver_candidates_cover_alerts",
                    "every alert has a bounded repair candidate",
                    True,
                    len(candidates) >= len(alerts),
                    "P1",
                    "add_bounded_repair_candidate_for_each_metric_alert",
                )
            )

    for raw_case in _as_sequence(custom_cases):
        if not isinstance(raw_case, Mapping):
            continue
        expected = raw_case.get("expected")
        actual = raw_case.get("actual")
        cases.append(
            _build_case(
                str(raw_case.get("case_id") or f"custom_case_{len(cases)+1}"),
                str(raw_case.get("name") or "custom regression case"),
                expected,
                actual,
                str(raw_case.get("severity") or "P2"),
                str(raw_case.get("failure_hint") or "review_custom_regression_case"),
            )
        )

    failed_cases = [case for case in cases if not case["passed"]]
    p0_failed = [case for case in failed_cases if case["severity"] == "P0"]
    if p0_failed:
        status = "BLOCK"
    elif failed_cases:
        status = "WARN"
    else:
        status = "PASS"

    report = {
        "schema": "PGGEvalRegressionHarness/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "case_count": len(cases),
        "passed_count": len(cases) - len(failed_cases),
        "failed_count": len(failed_cases),
        "p0_failed_count": len(p0_failed),
        "known_metric_count": known_metric_count,
        "alert_count": len(alerts),
        "candidate_count": len(candidates),
        "cases": cases,
        "failure_hints": [case["failure_hint"] for case in failed_cases if case.get("failure_hint")],
        "side_effects": "eval_report_write" if write_report else "read_only_eval",
        "boundary": "Local deterministic regression checks only; no model calls, code patches, or gene writes.",
        "agi_completion_claim": False,
    }
    report["eval_hash"] = _sha256_obj(report)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_eval_regression_harness.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


__all__ = ["build_eval_regression_harness"]
