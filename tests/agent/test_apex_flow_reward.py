from __future__ import annotations

import json
from pathlib import Path

from agent.apex_flow_reward import (
    build_flow_reward_report,
    load_latest_flow_reward_report,
    summarize_flow_reward_report,
    write_flow_reward_report,
)
from agent.apex_runtimeos_autonomy import summarize_autonomy_status
from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli


def _outcomes():
    return [
        {"id": "tests", "summary": "测试通过", "success": True, "reward": 0.95, "evidence": 0.95, "confidence": 0.9, "cost": 0.05, "risk": 0.05},
        {"id": "readback", "summary": "读回验证", "success": True, "reward": 0.9, "evidence": 0.9, "confidence": 0.85, "cost": 0.05, "risk": 0.05},
    ]


def test_build_flow_reward_report_scores_feedback_and_is_read_only():
    report = build_flow_reward_report(task="Flow test", selected_path_id="safe", predicted_score=0.76, outcomes=_outcomes())
    assert report["schema"] == "ApexFlowRewardReport/v1"
    assert report["status"] == "PASS"
    assert report["selected_path_id"] == "safe"
    assert report["outcome_count"] == 2
    assert report["realized_score"] >= 0.75
    assert report["executed_by_this_module"] is False
    assert report["routing_feedback_only"] is True
    assert all(item["side_effects"] == "observed_only" for item in report["outcomes"])


def test_flow_reward_report_sanitizes_sensitive_text():
    report = build_flow_reward_report(
        task="/Users/appleoppa/private api_key=secret",
        selected_path_id="safe",
        predicted_score=0.5,
        outcomes=[{"id": "x", "summary": "authorization: bearer ***", "success": False, "regression": 1.0}],
    )
    raw = json.dumps(report, ensure_ascii=False)
    assert "/Users/appleoppa" not in raw
    assert "api_key=secret" not in raw
    assert "authorization: bearer ***" not in raw


def test_write_and_load_latest_flow_reward_report_under_workspace():
    workspace = Path.cwd() / "workspace" / "flow_reward_test"
    workspace.mkdir(parents=True, exist_ok=True)
    report = build_flow_reward_report(task="Flow readback", selected_path_id="safe", predicted_score=0.7, outcomes=_outcomes())
    out = workspace / "flow.json"
    written = write_flow_reward_report(out, report)
    loaded = load_latest_flow_reward_report(workspace)
    assert written["written"] is True
    assert loaded is not None
    assert loaded["schema"] == "ApexFlowRewardSummary/v1"
    assert loaded["selected_path_id"] == "safe"
    assert loaded["routing_feedback_only"] is True


def test_write_flow_reward_report_rejects_outside_workspace(tmp_path):
    report = build_flow_reward_report(task="outside", selected_path_id="safe", predicted_score=0.7, outcomes=_outcomes())
    try:
        write_flow_reward_report(tmp_path / "flow.json", report)
    except ValueError as exc:
        assert "repository workspace" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_cli_flow_reward_json_report():
    workspace = Path.cwd() / "workspace" / "flow_reward_cli_test"
    workspace.mkdir(parents=True, exist_ok=True)
    out = workspace / "flow.json"
    payload = json.loads(run_apex_runtimeos_cli([
        "flow-reward",
        "--topic", "Flow CLI test",
        "--selected-path-id", "safe",
        "--predicted-score", "0.76",
        "--outcome", json.dumps(_outcomes()[0], ensure_ascii=False),
        "--outcome", json.dumps(_outcomes()[1], ensure_ascii=False),
        "--output", str(out),
        "--json",
    ]))
    report = payload["result"]["report"]
    assert payload["object"] == "hermes.apex_runtimeos.flow_reward"
    assert report["selected_path_id"] == "safe"
    assert report["executed_by_this_module"] is False
    assert payload["result"]["written"]["written"] is True


def test_summarize_flow_reward_report():
    report = build_flow_reward_report(task="sum", selected_path_id="safe", predicted_score=0.7, outcomes=_outcomes())
    summary = summarize_flow_reward_report(report)
    assert summary["valid"] is True
    assert summary["status"] == "PASS"
    assert summary["outcome_count"] == 2


def test_autonomy_status_reads_latest_flow_reward_report():
    workspace = Path.cwd() / "workspace" / "flow_reward"
    workspace.mkdir(parents=True, exist_ok=True)
    report = build_flow_reward_report(task="Flow status", selected_path_id="safe", predicted_score=0.7, outcomes=_outcomes())
    write_flow_reward_report(workspace / "flow_status.json", report)
    status = summarize_autonomy_status(limit=100)
    assert status["flow_reward_report"]["schema"] == "ApexFlowRewardSummary/v1"
    assert status["flow_reward_report"]["selected_path_id"] == "safe"
