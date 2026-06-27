"""PGG Archon eval-failure resolution packet builder.

This module converts P0 eval-regression failures into bounded, machine-checkable
resolution packets.  It does not lower eval thresholds, call models, patch core
code, write genes, or claim AGI completion; it only records whether each failed
case is expected-red or covered by a bounded repair candidate.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_PACKET_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/pgg-archon-eval-failure-packets")


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _safe_text(value: Any, limit: int = 300) -> str:
    return str(value or "")[:limit]


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _failed_cases(eval_regression_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in _as_sequence(eval_regression_report.get("cases")) if isinstance(item, Mapping) and not item.get("passed")]


def _repair_candidates(metric_driver: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in _as_sequence(metric_driver.get("repair_candidates")) if isinstance(item, Mapping)]


def _alerts(metric_driver: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in _as_sequence(metric_driver.get("alerts")) if isinstance(item, Mapping)]


def _candidate_metric_ids(candidates: Sequence[Mapping[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for candidate in candidates:
        metric_id = _safe_text(candidate.get("metric_id"), 120)
        if metric_id:
            ids.add(metric_id)
        trigger = candidate.get("trigger_alert")
        if isinstance(trigger, Mapping):
            trigger_id = _safe_text(trigger.get("metric_id"), 120)
            if trigger_id:
                ids.add(trigger_id)
    return ids


def build_pgg_archon_eval_failure_packet(
    eval_regression_report: Mapping[str, Any],
    metric_driver: Mapping[str, Any] | None = None,
    *,
    assertion_id_prefix: str = "pgg_archon_eval_failure",
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_PACKET_DIR,
) -> dict[str, Any]:
    """Build a bounded packet for current eval-regression failures."""
    metric_driver = dict(metric_driver or {})
    failed = _failed_cases(eval_regression_report)
    p0_failed = [case for case in failed if _safe_text(case.get("severity"), 20).upper() == "P0"]
    alerts = _alerts(metric_driver)
    p0_alerts = [alert for alert in alerts if _safe_text(alert.get("severity"), 20).upper() == "P0"]
    candidates = _repair_candidates(metric_driver)
    covered_metric_ids = _candidate_metric_ids(candidates)
    uncovered_p0_alert_metric_ids = [
        _safe_text(alert.get("metric_id"), 120) or "UNKNOWN"
        for alert in p0_alerts
        if (_safe_text(alert.get("metric_id"), 120) or "UNKNOWN") not in covered_metric_ids
    ]

    resolutions: list[dict[str, Any]] = []
    for index, case in enumerate(failed, 1):
        case_id = _safe_text(case.get("case_id"), 160) or f"unknown_failed_case_{index}"
        severity = _safe_text(case.get("severity"), 20).upper() or "P2"
        failure_hint = _safe_text(case.get("failure_hint"), 200)
        if case_id == "metric_driver_p0_alert_budget" and not uncovered_p0_alert_metric_ids and len(candidates) >= len(alerts):
            resolution_type = "BOUNDED_REPAIR_CANDIDATE_READY"
            completion_standard = "Every P0 metric alert is covered by a bounded repair candidate; eval remains red until the candidate is verified by its downstream gate."
        else:
            resolution_type = "EXPECTED_RED_REQUIRES_ASSERTION" if severity == "P0" else "WARN_REVIEW"
            completion_standard = "Failed eval must carry a stable assertion id, expected/actual values, and a bounded repair or explicit expected-red reason."
        resolutions.append({
            "assertion_id": f"{assertion_id_prefix}_{case_id}",
            "failed_case_id": case_id,
            "severity": severity,
            "expected": case.get("expected"),
            "actual": case.get("actual"),
            "failure_hint": failure_hint,
            "resolution_type": resolution_type,
            "completion_standard": completion_standard,
        })

    bounded_ready_count = sum(1 for item in resolutions if item.get("resolution_type") == "BOUNDED_REPAIR_CANDIDATE_READY")
    expected_red_count = sum(1 for item in resolutions if item.get("resolution_type") == "EXPECTED_RED_REQUIRES_ASSERTION")
    status = "PASS" if not failed else ("READY_FOR_REPAIR_GATE" if p0_failed and bounded_ready_count == len(p0_failed) and not uncovered_p0_alert_metric_ids else "HOLD")

    packet = {
        "schema": "PGGArchonEvalFailureResolutionPacket/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_eval_schema": eval_regression_report.get("schema"),
        "source_eval_status": eval_regression_report.get("status"),
        "source_failed_count": eval_regression_report.get("failed_count"),
        "failed_count": len(failed),
        "p0_failed_count": len(p0_failed),
        "alert_count": len(alerts) if metric_driver else eval_regression_report.get("alert_count"),
        "p0_alert_count": len(p0_alerts),
        "repair_candidate_count": len(candidates) if metric_driver else eval_regression_report.get("candidate_count"),
        "uncovered_p0_alert_metric_ids": uncovered_p0_alert_metric_ids,
        "bounded_ready_count": bounded_ready_count,
        "expected_red_count": expected_red_count,
        "resolution_status": status,
        "resolutions": resolutions,
        "blocked_side_effects": [
            "no_threshold_lowering",
            "no_core_patch",
            "no_gene_write",
            "no_autopromote",
            "no_agi_completion_claim",
        ],
        "not_executed": True,
        "side_effects": "packet_write" if write_report else "read_only_packet",
        "agi_completion_claim": False,
    }
    packet["packet_hash"] = _sha256_obj(packet)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_pgg_archon_eval_failure_packet.json"
        out.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        packet["report_path"] = str(out)
    return packet


__all__ = ["build_pgg_archon_eval_failure_packet"]
