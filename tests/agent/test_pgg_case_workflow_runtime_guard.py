from pathlib import Path

from agent.pgg_case_workflow_runtime_guard import (
    build_case_workflow_runtime_guard,
    has_case_start_trigger,
    infer_case_state_from_instruction,
    maybe_build_case_workflow_runtime_guard,
)


def test_detects_case_start_trigger():
    assert has_case_start_trigger("读取材料，启动办案程序") is True
    assert has_case_start_trigger("开始办案并建立案卷") is True
    assert has_case_start_trigger("普通法律咨询") is False


def test_infers_external_case_number_is_not_internal_pgg_number():
    state = infer_case_state_from_instruction("（2026）信仲字第50号案件，启动办案程序")
    assert state["case_id"] == "（2026）信仲字第50号"
    assert state["case_id_generated_by"] == "外部案号"
    assert state["formal_workflow_started"] is False


def test_infers_pgg_case_number_as_case_management_number():
    state = infer_case_state_from_instruction("PGG-ZY-20260528-003 开始办案")
    assert state["case_id"] == "PGG-ZY-20260528-003"
    assert state["case_id_generated_by"] == "案件管理中心"


def test_runtime_guard_blocks_degraded_case_start():
    payload = build_case_workflow_runtime_guard("读取材料，启动办案程序")
    assert payload["schema"] == "PGGCaseWorkflowRuntimeGuard/v1"
    assert payload["triggered"] is True
    assert payload["plan"]["preflight"]["status"] == "BLOCK"
    assert "案件管理中心" in payload["system_injection"]
    assert "不能把材料初筛说成正式办案完成" in payload["system_injection"]


def test_runtime_guard_persists_low_sensitive_audit(tmp_path, monkeypatch):
    audit_path = tmp_path / "guard.jsonl"
    monkeypatch.setenv("PGG_CASE_WORKFLOW_GUARD_AUDIT", str(audit_path))
    payload = maybe_build_case_workflow_runtime_guard("启动办案程序", session_id="s1", persist_audit=True)
    assert payload is not None
    data = audit_path.read_text(encoding="utf-8")
    assert "PGGCaseWorkflowRuntimeGuardAudit/v1" in data
    assert "case_start_trigger_not_formalized" in data
    assert "启动办案程序" not in data


def test_runtime_guard_ignores_non_case_turn(tmp_path, monkeypatch):
    audit_path = tmp_path / "guard.jsonl"
    monkeypatch.setenv("PGG_CASE_WORKFLOW_GUARD_AUDIT", str(audit_path))
    payload = maybe_build_case_workflow_runtime_guard("继续改进代码", session_id="s1", persist_audit=True)
    assert payload is None
    assert not audit_path.exists()
