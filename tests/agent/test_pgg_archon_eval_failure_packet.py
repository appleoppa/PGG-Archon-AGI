from __future__ import annotations

from pathlib import Path

from agent.capability_metric_driver import build_capability_metric_driver
from agent.eval_regression_harness import build_eval_regression_harness
from agent.pgg_archon_eval_failure_packet import build_pgg_archon_eval_failure_packet


def _blocked_metrics():
    return {
        "schema": "ApexRealCapabilityMetrics/v1",
        "status": "WATCH",
        "overall_score": 0.0,
        "agi_completion_claim": False,
        "metrics": {
            "multi_model_evidence": {
                "metric_id": "multi_model_evidence",
                "status": "UNKNOWN",
                "score": None,
                "missing": ["gpt_validator_not_pass", "claude_validator_not_pass"],
            }
        },
    }


def test_eval_failure_packet_marks_covered_p0_alert_as_bounded_repair_ready(tmp_path):
    driver = build_capability_metric_driver(_blocked_metrics())
    eval_report = build_eval_regression_harness(_blocked_metrics(), driver)

    packet = build_pgg_archon_eval_failure_packet(eval_report, driver, write_report=True, report_dir=tmp_path)

    assert packet["schema"] == "PGGArchonEvalFailureResolutionPacket/v1"
    assert packet["source_eval_status"] == "BLOCK"
    assert packet["resolution_status"] == "READY_FOR_REPAIR_GATE"
    assert packet["failed_count"] == 2
    assert packet["p0_failed_count"] == 1
    assert packet["bounded_ready_count"] == 1
    assert packet["uncovered_p0_alert_metric_ids"] == []
    p0_resolution = {item["failed_case_id"]: item for item in packet["resolutions"]}["metric_driver_p0_alert_budget"]
    assert p0_resolution["resolution_type"] == "BOUNDED_REPAIR_CANDIDATE_READY"
    assert "no_threshold_lowering" in packet["blocked_side_effects"]
    assert packet["not_executed"] is True
    assert packet["agi_completion_claim"] is False
    assert Path(packet["report_path"]).exists()


def test_eval_failure_packet_holds_when_p0_alert_is_uncovered():
    driver = build_capability_metric_driver(_blocked_metrics())
    driver["repair_candidates"] = []
    driver["candidate_count"] = 0
    eval_report = build_eval_regression_harness(_blocked_metrics(), driver)

    packet = build_pgg_archon_eval_failure_packet(eval_report, driver)

    assert packet["resolution_status"] == "HOLD"
    assert packet["bounded_ready_count"] == 0
    assert packet["uncovered_p0_alert_metric_ids"] == ["multi_model_evidence"]
    p0_resolution = {item["failed_case_id"]: item for item in packet["resolutions"]}["metric_driver_p0_alert_budget"]
    assert p0_resolution["resolution_type"] == "EXPECTED_RED_REQUIRES_ASSERTION"


def test_eval_failure_packet_passes_clean_eval_without_claiming_agi():
    metrics = {
        "schema": "ApexRealCapabilityMetrics/v1",
        "status": "PASS",
        "overall_score": 90.0,
        "agi_completion_claim": False,
        "metrics": {
            f"m{idx}": {"metric_id": f"m{idx}", "status": "PASS", "score": 90.0, "missing": []}
            for idx in range(1, 10)
        },
    }
    driver = build_capability_metric_driver(metrics)
    eval_report = build_eval_regression_harness(metrics, driver)

    packet = build_pgg_archon_eval_failure_packet(eval_report, driver)

    assert packet["resolution_status"] == "PASS"
    assert packet["failed_count"] == 0
    assert packet["resolutions"] == []
    assert packet["agi_completion_claim"] is False
