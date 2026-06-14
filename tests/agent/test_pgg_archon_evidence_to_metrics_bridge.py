from pathlib import Path

from agent.pgg_archon_evidence_to_metrics_bridge import bridge_evidence_to_metrics


def test_bridge_fresh_writes_eval_report_with_pass_data(tmp_path):
    result = bridge_evidence_to_metrics(write_eval_report=True, eval_report_dir=tmp_path)

    assert result["schema"] == "PGGArchonEvidenceToMetricsBridge/v1"
    assert result["agi_completion_claim"] is False

    # The bridge should produce a valid eval report from evidence loop data
    assert result["status"] in {"PASS", "WARN", "BLOCK"}
    assert result["metrics_known_count"] == 9
    assert result["eval_status"] == "PASS"
    assert result["eval_failed_count"] == 0
    assert result["pua_status"] == "PASS"
    assert result["not_executed"] is False

    # The eval report file should exist
    assert result["eval_report_path"]
    assert Path(result["eval_report_path"]).exists()

    # Verify the written file
    import json
    written = json.loads(Path(result["eval_report_path"]).read_text())
    assert written["schema"] == "PGGEvalRegressionHarness/v1"
    assert written["agi_completion_claim"] is False
    assert written["failed_count"] == 0
