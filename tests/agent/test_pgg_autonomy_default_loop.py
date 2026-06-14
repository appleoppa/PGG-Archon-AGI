from __future__ import annotations

from dataclasses import dataclass, field

from agent import pgg_autonomy_default_loop as loop


@dataclass
class DummyFix:
    target_path: str
    fix_type: str
    result: dict = field(default_factory=lambda: {"applied": True})


def test_auto_create_pr_skips_py_compile_only():
    result = loop.auto_create_pr_from_fixes([DummyFix("agent/foo.py", "py_compile")], [], loop.REPO)

    assert result[0]["status"] == "SKIP"
    assert "no code-modifying" in result[0]["reason"]


def test_auto_create_pr_reports_blocked_gh_auth_after_real_dirty_preflight(monkeypatch, tmp_path):
    monkeypatch.setattr(loop, "_git_tracked_change_count", lambda repo_dir: 1)
    monkeypatch.setattr(loop, "_gh_auth_ready", lambda repo_dir: {"ready": False, "reason": "token invalid"})

    result = loop.auto_create_pr_from_fixes([DummyFix("agent/foo.py", "ruff")], [], tmp_path)

    assert result[0]["status"] == "BLOCKED_GH_AUTH"
    assert "token invalid" in result[0]["reason"]


def test_auto_create_pr_skips_before_gh_auth_when_no_git_changes(monkeypatch, tmp_path):
    auth_called = False

    def fake_auth(repo_dir):
        nonlocal auth_called
        auth_called = True
        return {"ready": False, "reason": "token invalid"}

    monkeypatch.setattr(loop, "_git_tracked_change_count", lambda repo_dir: 0)
    monkeypatch.setattr(loop, "_gh_auth_ready", fake_auth)

    result = loop.auto_create_pr_from_fixes([DummyFix("agent/foo.py", "ruff")], [], tmp_path)

    assert result[0]["status"] == "SKIP"
    assert "no git changes" in result[0]["reason"]
    assert auth_called is False


def test_json_gate_probe_preserves_watch_json_status_and_score():
    res = {
        "rc": 2,
        "output": '{"status":"WATCH_INTERNAL_L2_CANDIDATE_READINESS","score":83.0,"summary":"13/16 components PASS"}',
    }

    probe = loop._json_gate_probe("l2_gate", res, 12.4)

    assert probe.status == "WATCH"
    assert "13/16 components PASS" in probe.summary
    assert "score=83.0" in probe.summary
    assert "rc=2" in probe.summary
    assert probe.details["data"]["status"] == "WATCH_INTERNAL_L2_CANDIDATE_READINESS"


def test_run_probes_calls_l2_and_agi_gates_with_json(monkeypatch):
    calls = []

    def fake_run(cmd, *, cwd=None, timeout=60):
        calls.append(cmd)
        joined = " ".join(cmd)
        if "pgg_l2_readiness_gate" in joined:
            return {"rc": 2, "output": '{"status":"WATCH_INTERNAL_L2_CANDIDATE_READINESS","score":83.0}'}
        if "pgg_agi_gap_closure_gate" in joined:
            return {"rc": 2, "output": '{"status":"WATCH_AGI_GAP_CLOSURE_PARTIAL","score":84.9}'}
        return {"rc": 0, "output": "{}"}

    monkeypatch.setattr(loop, "_run", fake_run)
    monkeypatch.setattr(loop, "_py_path", lambda: "python3")
    monkeypatch.setattr(loop, "HERMES_HOME", loop.Path("/definitely/missing/hermes"))

    probes = loop.run_probes()
    assert any(cmd[:4] == ["python3", "-m", "agent.pgg_l2_readiness_gate", "--json"] for cmd in calls)
    assert any(cmd[:4] == ["python3", "-m", "agent.pgg_agi_gap_closure_gate", "--json"] for cmd in calls)
    by_name = {p.name: p for p in probes}
    assert by_name["l2_gate"].details["data"]["score"] == 83.0
    assert by_name["agi_gap"].details["data"]["score"] == 84.9


def test_gene_intake_probe_prefers_rust_binary(monkeypatch, tmp_path):
    calls = []
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    rust_bin = bin_dir / "pgg_gene_intake_pipeline"
    rust_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    def fake_run(cmd, *, cwd=None, timeout=60):
        calls.append(cmd)
        return {
            "rc": 0,
            "output": '=== SCAN_SCORE ===\n{"scanned_files":7,"candidate_like_files":3,"top":[]}',
        }

    monkeypatch.setattr(loop, "HERMES_HOME", tmp_path)
    monkeypatch.setattr(loop, "_run", fake_run)
    probe = loop._run_gene_intake_probe("python3")

    assert probe.status == "PASS"
    assert "rust_scan_score" in probe.summary
    assert probe.details["native"] == "rust"
    assert calls and calls[0][0] == str(rust_bin)


def test_gene_intake_probe_falls_back_to_python_legacy(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, *, cwd=None, timeout=60):
        calls.append(cmd)
        return {"rc": 0, "output": '{"scanned":2,"fusion_dry_run_results":[1]}' }

    monkeypatch.setattr(loop, "HERMES_HOME", tmp_path)
    monkeypatch.setattr(loop, "_run", fake_run)
    probe = loop._run_gene_intake_probe("python3")

    assert probe.status == "PASS"
    assert "python_legacy" in probe.summary
    assert probe.details["native"] == "python_legacy"
    assert calls and calls[0][:3] == ["python3", "-m", "agent.pgg_gene_intake_loop_cli"]
