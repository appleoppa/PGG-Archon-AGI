from __future__ import annotations

import json

from agent import pgg_one_click_full_audit_gate as gate
from agent.pgg_one_click_full_audit_gate import build_status


def test_one_click_gate_uses_all_core_checks(monkeypatch):
    def fake_run(cmd, timeout=120, cwd=None):
        joined = " ".join(str(x) for x in cmd)
        if "hermes-goal" in joined:
            return {"returncode": 0, "stdout": '{"overall_status":"PASS","summary":"16/16 components PASS","watch_count":0,"blocked_count":0}', "stderr": ""}
        if "pgg_l2_readiness_gate" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_INTERNAL_L2_CANDIDATE_READINESS","score":86.8,"checks":{"agi_gap_ge_83":true},"component_statuses":{"agi_gap_source":"live"}}', "stderr": ""}
        if "omniroute_ui_status" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_OMNIROUTE_UI_PRACTICAL_READY_CONFIG_SYNC","passed":15,"total":15}', "stderr": ""}
        if "pgg_omniroute_provider_probe_gate" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_OMNIROUTE_PROVIDER_PROBE_GATE_V109","passed":31,"total":31}', "stderr": ""}
        if "pgg_provider_cost_profile" in joined:
            return {"returncode": 0, "stdout": '{"profiles":{"ark":{},"deepseek":{},"mimo":{},"agnes":{},"gpt":{},"claude":{}},"global_cost_order":["ark","deepseek","mimo","agnes","gpt","claude"]}', "stderr": ""}
        if "pgg_guarded_production_enable_gate" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_GUARDED_STRICT_EXACT_GENERAL_PRODUCTION_ACTIVE","passed":10,"total":10}', "stderr": ""}
        if "记忆系统" in joined:
            return {"returncode": 0, "stdout": '{"overall":{"score_percent":100.0,"failed_or_watch":[]}}', "stderr": ""}
        if "神经元系统" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS"}', "stderr": ""}
        if "pytest" in joined:
            return {"returncode": 0, "stdout": '7 passed in 0.10s', "stderr": ""}
        if "docker info" in joined:
            return {"returncode": 0, "stdout": '29.5.2\n', "stderr": ""}
        raise AssertionError(joined)

    monkeypatch.setattr("agent.pgg_one_click_full_audit_gate._run", fake_run)
    monkeypatch.setattr("agent.pgg_one_click_full_audit_gate._memory_system_status", lambda: (0, {"overall": {"score_percent": 100.0, "failed_or_watch": []}}))
    rec = build_status()
    assert rec["status"] == "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION"
    assert rec["passed"] == rec["total"] == 11
    assert any(c["name"] == "l2_readiness_live_agi_gap_pass" and c["ok"] for c in rec["checks"])


def test_one_click_gate_updates_latest_snapshot_atomically(monkeypatch, tmp_path, capsys):
    rec = {
        "schema": "PGGOneClickFullAuditAntiRegressionGate/v1",
        "status": "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION",
        "passed": 1,
        "total": 1,
        "checks": [{"name": "probe", "ok": True}],
    }
    monkeypatch.setattr(gate, "HOME", tmp_path)
    monkeypatch.setattr(gate, "build_status", lambda run_provider_canary=False, provider="deepseek": rec)

    assert gate.main(["--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    latest = tmp_path / ".hermes/data/pgg_one_click_full_audit_gate_latest.json"
    ledger = tmp_path / ".hermes/data/pgg_one_click_full_audit_gate_ledger.jsonl"

    assert latest.exists()
    assert ledger.exists()
    assert json.loads(latest.read_text(encoding="utf-8")) == printed
    assert json.loads(ledger.read_text(encoding="utf-8").strip()) == printed
