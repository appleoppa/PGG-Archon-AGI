"""Capability metric driver for PGG Archon.

This module turns read-only capability metrics into threshold alerts and bounded
repair candidates. It does not mutate the gene database, call models, or claim
AGI completion.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

DEFAULT_DRIVER_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/capability-metric-driver")
DEFAULT_THRESHOLDS = {
    "factual_grounding": 70.0,
    "evidence_chain": 70.0,
    "legal_basis_verification": 70.0,
    "tool_verified_execution": 80.0,
    "delivery_completion": 75.0,
    "failure_learning": 80.0,
    "task_retrospective": 80.0,
    "low_risk_autonomy": 60.0,
    "multi_model_evidence": 80.0,
}
_REPAIR_MAP = {
    "factual_grounding": "require_source_bound_fact_check_event",
    "evidence_chain": "require_artifact_hash_before_delivery",
    "legal_basis_verification": "require_verified_statute_or_case_source",
    "tool_verified_execution": "require_test_or_tool_verification_event",
    "delivery_completion": "require_delivery_or_blocked_internal_report_event",
    "failure_learning": "append_failure_sample_with_next_intercept_method",
    "task_retrospective": "append_three_question_retrospective",
    "low_risk_autonomy": "generate_low_risk_candidate_with_review_gate",
    "multi_model_evidence": "require_gpt_claude_or_policy_fallback_evidence",
}


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _metric_items(summary: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    metrics = summary.get("metrics")
    if isinstance(metrics, Mapping):
        return [m for m in metrics.values() if isinstance(m, Mapping)]
    if isinstance(metrics, list):
        return [m for m in metrics if isinstance(m, Mapping)]
    return []


def build_capability_metric_driver(
    metrics_summary: Mapping[str, Any],
    *,
    thresholds: Mapping[str, float] | None = None,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_DRIVER_DIR,
) -> dict[str, Any]:
    threshold_map = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        threshold_map.update({str(k): float(v) for k, v in thresholds.items()})
    alerts: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for metric in _metric_items(metrics_summary):
        metric_id = str(metric.get("metric_id") or "")
        status = str(metric.get("status") or "UNKNOWN")
        score = metric.get("score")
        threshold = threshold_map.get(metric_id, 70.0)
        missing = list(metric.get("missing") or []) if isinstance(metric.get("missing"), list) else []
        below = score is None or float(score) < threshold
        unhealthy = status in {"UNKNOWN", "WATCH", "BLOCK"} or below
        if not unhealthy:
            continue
        severity = "P0" if status in {"UNKNOWN", "BLOCK"} or score is None else ("P1" if float(score) < threshold * 0.75 else "P2")
        alert = {
            "metric_id": metric_id,
            "status": status,
            "score": score,
            "threshold": threshold,
            "severity": severity,
            "missing": missing,
            "reason": "metric_unknown_or_below_threshold" if below else "metric_watch_or_block",
        }
        alerts.append(alert)
        candidates.append({
            "schema": "CapabilityMetricRepairCandidate/v1",
            "candidate_id": f"capability_metric_{metric_id}_{int(time.time())}",
            "metric_id": metric_id,
            "repair_rule": _REPAIR_MAP.get(metric_id, "manual_metric_repair_review"),
            "trigger_alert": alert,
            "risk": "low" if severity != "P0" else "low-medium",
            "requires_human_or_next_gate": True,
            "not_written_to_gene_db": True,
            "agi_completion_claim": False,
        })
    driver = {
        "schema": "PGGCapabilityMetricDriver/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_schema": metrics_summary.get("schema"),
        "source_status": metrics_summary.get("status"),
        "overall_score": metrics_summary.get("overall_score"),
        "alert_count": len(alerts),
        "candidate_count": len(candidates),
        "alerts": alerts,
        "repair_candidates": candidates,
        "final_recommendation": "generate_repair_candidates" if candidates else "no_metric_repair_needed",
        "side_effects": "driver_report_write" if write_report else "read_only_driver",
        "agi_completion_claim": False,
    }
    driver["driver_hash"] = _sha256_obj(driver)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_capability_metric_driver.json"
        out.write_text(json.dumps(driver, ensure_ascii=False, indent=2), encoding="utf-8")
        driver["report_path"] = str(out)
    return driver


__all__ = ["build_capability_metric_driver"]
