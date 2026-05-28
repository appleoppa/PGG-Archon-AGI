from __future__ import annotations

from agent.pgg_case_workflow_entry import plan_case_workflow_entry


def _actions(plan: dict) -> set[str]:
    return {action["action"] for action in plan["actions"]}


def test_start_instruction_plans_formal_case_workflow_actions():
    plan = plan_case_workflow_entry("读取材料，启动办案程序。", {
        "formal_workflow_started": False,
        "evidence_gate_status": "HOLD",
        "internal_report_generated": False,
    })
    actions = _actions(plan)
    assert plan["status"] == "ACTION_REQUIRED"
    assert "request_case_management_numbering" in actions
    assert "create_standard_case_task_pack" in actions
    assert "dispatch_parallel_departments" in actions
    assert "generate_internal_case_process_report" in actions
    assert plan["allows_external_delivery"] is False


def test_entry_plans_amount_closure_before_formal_document():
    plan = plan_case_workflow_entry("继续办案", {
        "formal_workflow_started": True,
        "case_id": "PGG-FW-20260528-002",
        "case_id_generated_by": "案件管理中心",
        "amount_versions": [629710.20, 627910.20],
        "amount_delta_explained": False,
        "evidence_gate_status": "PASS",
        "internal_report_generated": True,
    })
    assert "build_amount_closure_table" in _actions(plan)
    assert plan["allows_external_delivery"] is False


def test_entry_downgrades_formal_output_when_evidence_hold():
    plan = plan_case_workflow_entry("生成正式起诉状", {
        "formal_workflow_started": True,
        "case_id": "PGG-MS-20260528-001",
        "case_id_generated_by": "案件管理中心",
        "evidence_gate_status": "HOLD",
        "intended_output": "正式起诉状终版",
        "internal_report_generated": True,
    })
    actions = _actions(plan)
    assert "downgrade_to_internal_draft" in actions
    assert plan["preflight"]["status"] == "BLOCK"


def test_entry_voids_unauthorized_case_number():
    plan = plan_case_workflow_entry("开始办案", {
        "formal_workflow_started": True,
        "case_id": "CASE-20260528-081253",
        "case_id_generated_by": "中枢",
        "evidence_gate_status": "PASS",
        "internal_report_generated": True,
    })
    assert "void_unauthorized_case_number" in _actions(plan)
    assert plan["allows_external_delivery"] is False


def test_entry_clean_case_allows_external_delivery():
    plan = plan_case_workflow_entry("继续办案", {
        "formal_workflow_started": True,
        "case_id": "PGG-MS-20260528-001",
        "case_id_generated_by": "案件管理中心",
        "department_results": [{"department": "证据管理部", "status": "COMPLETED"}],
        "amount_versions": [800000],
        "amount_delta_explained": True,
        "evidence_gate_status": "PASS",
        "intended_output": "正式对外交付",
        "internal_report_generated": True,
    })
    assert plan["status"] == "PASS"
    assert plan["action_count"] == 0
    assert plan["allows_external_delivery"] is True
