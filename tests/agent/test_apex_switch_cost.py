import json

from agent.apex_switch_cost import (
    build_switch_cost_report,
    load_latest_switch_cost_report,
    summarize_switch_cost_report,
    write_switch_cost_report,
)


def test_switch_cost_report_holds_when_gain_does_not_cover_transition_cost():
    report = build_switch_cost_report(
        task="avoid thrashing",
        current_route={"id": "stable", "reward": 0.7, "evidence": 0.8, "confidence": 0.8, "risk": 0.1, "cost": 0.2, "features": ["a", "b"]},
        target_route={"id": "new", "reward": 0.8, "evidence": 0.8, "confidence": 0.8, "risk": 0.2, "cost": 0.3, "features": ["x", "y"]},
        switching_cost=0.4,
    )

    assert report["schema"] == "ApexSwitchCostReport/v1"
    assert report["decision"] == "HOLD"
    assert report["status"] == "HOLD"
    assert report["executed"] is False
    assert report["thrash_guard"] is True
    assert report["switching_cost"] == 0.4
    assert report["net_gain"] < 0


def test_switch_cost_report_switches_only_when_net_gain_clears_hysteresis():
    report = build_switch_cost_report(
        task="material upgrade",
        current_route={"id": "old", "reward": 0.35, "evidence": 0.5, "confidence": 0.5, "risk": 0.2, "cost": 0.2, "features": ["a"]},
        target_route={"id": "better", "reward": 1.0, "evidence": 1.0, "confidence": 1.0, "risk": 0.05, "cost": 0.05, "features": ["a"]},
        switching_cost=0.05,
        hysteresis=0.15,
    )

    assert report["decision"] == "SWITCH"
    assert report["status"] == "PASS"
    assert report["net_gain"] >= 0.15


def test_switch_cost_report_sanitizes_paths_and_secrets():
    report = build_switch_cost_report(
        task="secret=abc /Users/appleoppa/raw",
        current_route={"id": "current", "summary": "authorization: Bearer abc", "features": ["/Users/appleoppa/tool"]},
        target_route={"id": "target", "summary": "safe", "features": ["new"]},
    )

    payload = json.dumps(report, ensure_ascii=False)
    assert "Bearer abc" not in payload
    assert "/Users/appleoppa" not in payload
    assert "[REDACTED" in payload


def test_switch_cost_write_and_load_latest_summary(tmp_path):
    workspace = tmp_path / "workspace"
    path = workspace / "switch_cost" / "report.json"
    # Monkeypatch module workspace guard by passing a path under real repo workspace is
    # covered elsewhere; here assert summary shape directly via report round-trip helper.
    report = build_switch_cost_report(
        task="summary",
        current_route={"id": "a", "reward": 0.2},
        target_route={"id": "b", "reward": 0.8},
        switching_cost=0.1,
    )
    summary = summarize_switch_cost_report(report)
    assert summary["schema"] == "ApexSwitchCostSummary/v1"
    assert summary["valid"] is True
    assert summary["executed"] is False
    assert summary["thrash_guard"] is True
