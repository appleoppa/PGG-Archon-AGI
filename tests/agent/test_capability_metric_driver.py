from pathlib import Path

from agent.capability_metric_driver import build_capability_metric_driver


def _summary(metrics):
    return {
        "schema": "ApexRealCapabilityMetrics/v1",
        "status": "WATCH",
        "overall_score": 65.0,
        "metrics": metrics,
    }


def test_metric_driver_generates_alert_for_unknown_metric(tmp_path):
    driver = build_capability_metric_driver(
        _summary({"multi_model_evidence": {"metric_id": "multi_model_evidence", "status": "UNKNOWN", "score": None, "missing": ["no_multi_model_records"]}}),
        write_report=True,
        report_dir=tmp_path,
    )
    assert driver["alert_count"] == 1
    assert driver["candidate_count"] == 1
    assert driver["alerts"][0]["severity"] == "P0"
    assert driver["repair_candidates"][0]["repair_rule"] == "require_gpt_claude_or_policy_fallback_evidence"
    assert Path(driver["report_path"]).exists()
    assert driver["agi_completion_claim"] is False


def test_metric_driver_generates_candidate_for_below_threshold_watch():
    driver = build_capability_metric_driver(
        _summary({"delivery_completion": {"metric_id": "delivery_completion", "status": "WATCH", "score": 40.0, "missing": []}})
    )
    assert driver["final_recommendation"] == "generate_repair_candidates"
    assert driver["alerts"][0]["severity"] == "P1"
    assert driver["repair_candidates"][0]["not_written_to_gene_db"] is True


def test_metric_driver_noops_for_passing_metrics():
    driver = build_capability_metric_driver(
        _summary({"tool_verified_execution": {"metric_id": "tool_verified_execution", "status": "PASS", "score": 95.0, "missing": []}})
    )
    assert driver["alert_count"] == 0
    assert driver["candidate_count"] == 0
    assert driver["final_recommendation"] == "no_metric_repair_needed"
