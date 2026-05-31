"""
Tests for agent/pgg_archon_auto_git_push.py
"""
import json
import pytest
from pathlib import Path

from agent.pgg_archon_auto_git_push import _check_gates


def _make_phase9(tmp_path, status="ci_drift_gate_passed", blockers=None):
    p = tmp_path / "phase9.json"
    p.write_text(json.dumps({"status": status, "blockers": blockers or [], "score": 87.417}), encoding="utf-8")
    return p


def _make_policy(tmp_path, enabled=True, push_auth=True):
    p = tmp_path / "policy.json"
    p.write_text(json.dumps({
        "enabled": enabled,
        "operator_authorization": "test",
        "authorized_actions": {"auto_git_push_after_tests": push_auth},
        "hard_gates": {},
    }), encoding="utf-8")
    return p


def _make_deploy_log(tmp_path, decision="deployed"):
    d = tmp_path / "phase10_deploy_log.json"
    d.write_text(json.dumps({"decision": decision, "ts": 0}), encoding="utf-8")
    return d


def test_check_gates_passes_when_all_ok(tmp_path, monkeypatch):
    phase9 = _make_phase9(tmp_path)
    policy = _make_policy(tmp_path)
    deploy_log = _make_deploy_log(tmp_path)
    import agent.pgg_archon_auto_git_push as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", policy)
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", phase9)
    monkeypatch.setattr(mod, "_DEFAULT_DEPLOY_LOG", deploy_log)
    ok, blockers = _check_gates()
    assert ok is True
    assert blockers == []


def test_check_gates_blocks_when_deploy_not_done(tmp_path, monkeypatch):
    _make_policy(tmp_path)
    _make_phase9(tmp_path)
    _make_deploy_log(tmp_path, decision="blocked")
    import agent.pgg_archon_auto_git_push as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", tmp_path / "policy.json")
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", tmp_path / "phase9.json")
    monkeypatch.setattr(mod, "_DEFAULT_DEPLOY_LOG", tmp_path / "phase10_deploy_log.json")
    ok, blockers = _check_gates()
    assert ok is False
    assert "deployment_not_confirmed" in blockers


def test_check_gates_blocks_when_phase9_not_passed(tmp_path, monkeypatch):
    _make_policy(tmp_path)
    _make_phase9(tmp_path, status="ci_drift_gate_failed")
    _make_deploy_log(tmp_path)
    import agent.pgg_archon_auto_git_push as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", tmp_path / "policy.json")
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", tmp_path / "phase9.json")
    monkeypatch.setattr(mod, "_DEFAULT_DEPLOY_LOG", tmp_path / "phase10_deploy_log.json")
    ok, blockers = _check_gates()
    assert ok is False
    assert "phase9_not_passed" in blockers


def test_check_gates_blocks_when_push_not_authorized(tmp_path, monkeypatch):
    _make_policy(tmp_path, push_auth=False)
    _make_phase9(tmp_path)
    _make_deploy_log(tmp_path)
    import agent.pgg_archon_auto_git_push as mod
    monkeypatch.setattr(mod, "_DEFAULT_POLICY", tmp_path / "policy.json")
    monkeypatch.setattr(mod, "_DEFAULT_PHASE9", tmp_path / "phase9.json")
    monkeypatch.setattr(mod, "_DEFAULT_DEPLOY_LOG", tmp_path / "phase10_deploy_log.json")
    ok, blockers = _check_gates()
    assert ok is False
    assert "push_not_authorized_in_policy" in blockers
