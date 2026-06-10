from __future__ import annotations

import json

from agent import pgg_unfinished_items_gate as gate


def test_unfinished_items_gate_separates_active_from_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "DATA", tmp_path)
    monkeypatch.setattr(gate, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "ledger.jsonl")
    for name in gate.HISTORICAL_WATCH_FILES:
        (tmp_path / name).write_text(json.dumps({"status": "WATCH_OLD_SURFACE"}), encoding="utf-8")

    def fake_run(cmd, timeout=60):
        joined = " ".join(map(str, cmd))
        if "git status" in joined:
            return {"returncode": 0, "stdout": "", "stderr": ""}
        return {"returncode": 0, "stdout": "[]", "stderr": ""}

    def fake_json(cmd, timeout=90):
        joined = " ".join(map(str, cmd))
        if "gh pr list" in joined:
            return []
        if "hermes-goal" in joined:
            return {"summary": "16/16 components PASS", "watch_count": 0, "blocked_count": 0}
        if "pgg_one_click_full_audit_gate" in joined:
            return {"status": "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION", "passed": 9, "total": 9}
        if "pgg_l2_readiness_gate" in joined:
            return {"status": "PASS_INTERNAL_L2_CANDIDATE_READINESS", "score": 86.8}
        return {}

    monkeypatch.setattr(gate, "_run", fake_run)
    monkeypatch.setattr(gate, "_json", fake_json)
    rec = gate.build_status()
    assert rec["status"] == "PASS_NO_ACTIVE_UNFINISHED_ITEMS"
    assert rec["active_unfinished_count"] == 0
    assert rec["stale_historical_watch_count"] == len(gate.HISTORICAL_WATCH_FILES)
    assert "not current blockers" in rec["boundary"]
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "ledger.jsonl").exists()


def test_unfinished_items_gate_reports_dirty_as_active(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "DATA", tmp_path)
    monkeypatch.setattr(gate, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "ledger.jsonl")

    def fake_run(cmd, timeout=60):
        joined = " ".join(map(str, cmd))
        if "git status" in joined:
            return {"returncode": 0, "stdout": "?? scratch.py\n", "stderr": ""}
        return {"returncode": 0, "stdout": "[]", "stderr": ""}

    monkeypatch.setattr(gate, "_run", fake_run)
    monkeypatch.setattr(gate, "_json", lambda cmd, timeout=90: [] if "gh" in " ".join(map(str, cmd)) else {"summary": "16/16 components PASS", "watch_count": 0, "blocked_count": 0, "status": "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION", "passed": 9, "total": 9, "score": 86.8})
    rec = gate.build_status()
    assert rec["status"] == "WATCH_ACTIVE_UNFINISHED_ITEMS"
    assert rec["active_unfinished"][0]["kind"] == "git_dirty"
