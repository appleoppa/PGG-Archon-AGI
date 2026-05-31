"""
Tests for agent/pgg_archon_auto_deploy.py
"""
import json
import pytest
from pathlib import Path

from agent.pgg_archon_auto_deploy import _check_gates, run_auto_deploy


def _make_phase9(tmp_path, status="ci_drift_gate_passed", blockers=None):
    p = tmp_path / "phase9.json"
    p.write_text(json.dumps({"status": status, "blockers": blockers or [], "score": 87.417}), encoding="utf-8")
    return p


def _make_policy(tmp_path, enabled=True, deploy_auth=True):
    p = tmp_path / "policy.json"
    p.write_text(json.dumps({
        "enabled": enabled,
        "operator_authorization": "test",
        "authorized_actions": {"auto_deploy_after_tests": deploy_auth},
        "hard_gates": {},
    }), encoding="utf-8")
    return p


def test_check_gates_passes_when_all_gates_ok(tmp_path, monkeypatch):
    phase9 = _make_phase9(tmp_path)
    policy = _make_policy(tmp_path)
    import agent.pgg_archon_auto_deploy as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", policy)
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", phase9)
    ok, blockers = _check_gates()
    assert ok is True
    assert blockers == []


def test_check_gates_blocks_when_phase9_fails(tmp_path, monkeypatch):
    _make_policy(tmp_path)
    p9 = _make_phase9(tmp_path, status="ci_drift_gate_failed")
    import agent.pgg_archon_auto_deploy as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", p9.parent / "policy.json")
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", p9)
    ok, blockers = _check_gates()
    assert ok is False
    assert "phase9_status=ci_drift_gate_failed" in blockers


def test_check_gates_blocks_when_policy_disabled(tmp_path, monkeypatch):
    _make_policy(tmp_path, enabled=False)
    p9 = _make_phase9(tmp_path)
    import agent.pgg_archon_auto_deploy as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", p9.parent / "policy.json")
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", p9)
    ok, blockers = _check_gates()
    assert ok is False
    assert "policy_disabled_or_missing" in blockers


def test_run_auto_deploy_blocks_without_gates(tmp_path, monkeypatch):
    p9 = _make_phase9(tmp_path, status="ci_drift_gate_failed")
    import agent.pgg_archon_auto_deploy as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", p9.parent / "policy.json")
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", p9)
    result = run_auto_deploy()
    assert result["allowed"] is False
    assert result["decision"] == "blocked"
    assert len(result["blockers"]) > 0
