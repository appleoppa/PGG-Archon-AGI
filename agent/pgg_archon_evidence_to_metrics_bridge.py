"""PGG Archon evidence-to-metrics bridge.

Connects the evidence loop surface's populated capability metrics into the eval
regression harness and writes the result so the status surface picks it up.
This is a bounded, read-only, verifiable bridge — it does not lower thresholds,
patch core, write genes, call models, or claim AGI completion.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from agent.capability_metric_driver import build_capability_metric_driver
from agent.eval_regression_harness import build_eval_regression_harness
from agent.pgg_archon_evidence_loop_surface import build_pgg_archon_evidence_loop_surface
from agent.pgg_archon_pua_standards import build_pgg_archon_pua_standard_report

DEFAULT_EVAL_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/eval-regression-harness")


def bridge_evidence_to_metrics(
    *,
    write_eval_report: bool = True,
    eval_report_dir: str | Path = DEFAULT_EVAL_DIR,
) -> dict[str, Any]:
    """Bridge evidence loop data into a fresh eval regression report.

    Returns a structured bridge report showing what was generated.
    Does not modify any core code, genes, or status files.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # 1. Get evidence loop data (already populates capability metrics from real sources)
    evidence = build_pgg_archon_evidence_loop_surface()
    capability_metrics = dict(evidence.get("real_capability_metrics") or {})

    if not capability_metrics or not capability_metrics.get("metrics"):
        return {
            "schema": "PGGArchonEvidenceToMetricsBridge/v1",
            "created_at": ts,
            "status": "HOLD",
            "reason": "evidence_loop_has_no_capability_metrics",
            "evidence_loop_status": evidence.get("status"),
            "side_effects": "read_only_bridge",
            "not_executed": True,
            "agi_completion_claim": False,
        }

    # 2. Build metric driver from populated metrics
    driver = build_capability_metric_driver(capability_metrics)

    # 3. Build eval regression from populated data
    eval_report = build_eval_regression_harness(
        capability_metrics,
        driver,
        write_report=write_eval_report,
        report_dir=str(eval_report_dir),
    )

    # 4. Also build PUA standards for completeness
    pua = build_pgg_archon_pua_standard_report()

    return {
        "schema": "PGGArchonEvidenceToMetricsBridge/v1",
        "created_at": ts,
        "status": eval_report.get("status"),
        "evidence_loop_status": evidence.get("status"),
        "metrics_status": capability_metrics.get("status"),
        "metrics_score": capability_metrics.get("overall_score"),
        "metrics_known_count": capability_metrics.get("known_metric_count"),
        "eval_status": eval_report.get("status"),
        "eval_failed_count": eval_report.get("failed_count"),
        "eval_report_path": eval_report.get("report_path"),
        "pua_status": pua.get("p0_status"),
        "bridge_action": "eval_report_written" if write_eval_report else "read_only_diagnosis",
        "side_effects": "eval_report_write_only" if write_eval_report else "read_only_bridge",
        "not_executed": False,
        "agi_completion_claim": False,
    }


__all__ = ["bridge_evidence_to_metrics"]
