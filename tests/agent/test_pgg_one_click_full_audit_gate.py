from __future__ import annotations

from agent.pgg_one_click_full_audit_gate import build_status


def test_one_click_gate_uses_all_core_checks(monkeypatch):
    def fake_run(cmd, timeout=120, cwd=None):
        joined = " ".join(str(x) for x in cmd)
        if "hermes-goal" in joined:
            return {"returncode": 0, "stdout": '{"overall_status":"PASS","summary":"16/16 components PASS","watch_count":0,"blocked_count":0}', "stderr": ""}
        if "omniroute_ui_status" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_OMNIROUTE_UI_PRACTICAL_READY_CONFIG_SYNC","passed":15,"total":15}', "stderr": ""}
        if "pgg_omniroute_provider_probe_gate" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_OMNIROUTE_PROVIDER_PROBE_GATE_V109","passed":31,"total":31}', "stderr": ""}
        if "pgg_guarded_production_enable_gate" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_GUARDED_STRICT_EXACT_GENERAL_PRODUCTION_ACTIVE","passed":10,"total":10}', "stderr": ""}
        if "记忆系统" in joined:
            return {"returncode": 0, "stdout": '{"overall":{"score_percent":100.0,"failed_or_watch":[]}}', "stderr": ""}
        if "神经元系统" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS"}', "stderr": ""}
        if "pytest" in joined:
            return {"returncode": 0, "stdout": '6 passed in 0.10s', "stderr": ""}
        if "docker info" in joined:
            return {"returncode": 0, "stdout": '29.5.2\n', "stderr": ""}
        raise AssertionError(joined)

    monkeypatch.setattr("agent.pgg_one_click_full_audit_gate._run", fake_run)
    rec = build_status()
    assert rec["status"] == "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION"
    assert rec["passed"] == rec["total"] == 8
