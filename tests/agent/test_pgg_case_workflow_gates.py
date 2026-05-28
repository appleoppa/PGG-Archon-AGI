from __future__ import annotations

from agent.pgg_case_workflow_gates import evaluate_case_workflow_preflight


def _codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


def test_start_case_instruction_must_formalize_workflow():
    result = evaluate_case_workflow_preflight({
        "user_instruction": "读取材料，启动办案程序。",
        "formal_workflow_started": False,
        "internal_report_generated": True,
        "evidence_gate_status": "HOLD",
    })
    assert result["status"] == "BLOCK"
    assert "case_start_trigger_not_formalized" in _codes(result)


def test_case_number_must_be_generated_by_case_management():
    result = evaluate_case_workflow_preflight({
        "case_id": "CASE-20260528-081253",
        "case_id_generated_by": "中枢",
        "formal_workflow_started": True,
        "internal_report_generated": True,
        "evidence_gate_status": "PASS",
    })
    assert result["status"] == "BLOCK"
    assert "case_number_not_authorized_by_case_management" in _codes(result)


def test_department_timeout_requires_exception_label():
    result = evaluate_case_workflow_preflight({
        "formal_workflow_started": True,
        "case_id": "PGG-MS-20260528-001",
        "case_id_generated_by": "案件管理中心",
        "department_results": [{"department": "证据管理部", "status": "TIMEOUT", "exception_labeled": False}],
        "internal_report_generated": True,
        "evidence_gate_status": "HOLD",
    })
    assert result["status"] == "BLOCK"
    assert "department_exception_without_label" in _codes(result)


def test_amount_versions_without_explanation_hold():
    result = evaluate_case_workflow_preflight({
        "formal_workflow_started": True,
        "case_id": "PGG-FW-20260528-002",
        "case_id_generated_by": "案件管理中心",
        "amount_versions": [629710.20, 627910.20],
        "amount_delta_explained": False,
        "internal_report_generated": True,
        "evidence_gate_status": "PASS",
    })
    assert result["status"] == "HOLD"
    assert "amount_versions_without_closure" in _codes(result)


def test_formal_delivery_blocked_when_evidence_gate_hold():
    result = evaluate_case_workflow_preflight({
        "formal_workflow_started": True,
        "case_id": "PGG-MS-20260528-001",
        "case_id_generated_by": "案件管理中心",
        "evidence_gate_status": "HOLD",
        "intended_output": "正式起诉状终版，对外交付",
        "internal_report_generated": True,
    })
    assert result["status"] == "BLOCK"
    assert "formal_delivery_with_evidence_gate_hold" in _codes(result)
    assert result["allows_external_delivery"] is False


def test_delivery_blocked_requires_internal_report():
    result = evaluate_case_workflow_preflight({
        "formal_workflow_started": True,
        "case_id": "PGG-MS-20260528-001",
        "case_id_generated_by": "案件管理中心",
        "evidence_gate_status": "HOLD",
        "internal_report_generated": False,
    })
    assert result["status"] == "BLOCK"
    assert "delivery_blocked_without_internal_report" in _codes(result)


def test_clean_case_preflight_passes_and_allows_delivery():
    result = evaluate_case_workflow_preflight({
        "user_instruction": "开始办案",
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
    assert result["status"] == "PASS"
    assert result["issue_count"] == 0
    assert result["allows_external_delivery"] is True
