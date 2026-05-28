from pathlib import Path

from agent.case_flow_orchestrator_ledger import build_case_flow_orchestrator_ledger, summarize_case_flow_ledgers


def test_case_flow_ledger_blocks_unformalized_case_start_and_missing_report(tmp_path):
    ledger = build_case_flow_orchestrator_ledger(
        "启动办案程序",
        {
            "case_id": "TEMP-001",
            "case_id_generated_by": "苹果中枢",
            "formal_workflow_started": False,
            "evidence_gate_status": "HOLD",
            "intended_output": "正式律师函",
            "internal_report_generated": False,
            "department_results": [],
        },
        write_ledger=True,
        ledger_dir=tmp_path,
    )
    assert ledger["status"] == "BLOCK"
    assert ledger["preflight_status"] == "BLOCK"
    assert ledger["entry_action_count"] >= 3
    assert "案件管理中心" in ledger["missing_departments"]
    assert ledger["allows_external_delivery"] is False
    assert Path(ledger["ledger_path"]).exists()
    assert ledger["agi_completion_claim"] is False


def test_case_flow_ledger_marks_unlabeled_department_exception_as_block():
    ledger = build_case_flow_orchestrator_ledger(
        "开始办案",
        {
            "case_id": "PGG-MS-20260528-001",
            "case_id_generated_by": "案件管理中心",
            "formal_workflow_started": True,
            "evidence_gate_status": "PASS",
            "intended_output": "内部分析",
            "internal_report_generated": True,
            "department_results": [
                {"department": "案件管理中心", "status": "PASS"},
                {"department": "证据管理部", "status": "TIMEOUT", "exception_labeled": False},
            ],
        },
    )
    assert ledger["status"] == "BLOCK"
    assert ledger["blocking_department_event_count"] == 1
    event = [x for x in ledger["events"] if x["owner"] == "证据管理部"][0]
    assert event["remediation"] == "mark_department_exception_and_retry_or_compensate"


def test_case_flow_ledger_passes_when_all_departments_complete_and_gate_passes():
    departments = [
        {"department": name, "status": "PASS", "evidence_hash": f"h-{idx}"}
        for idx, name in enumerate(("案件管理中心", "证据管理部", "主办部门", "律法支持部", "案件推演部", "智脑知识部"), 1)
    ]
    ledger = build_case_flow_orchestrator_ledger(
        "启动办案程序",
        {
            "case_id": "PGG-MS-20260528-001",
            "case_id_generated_by": "案件管理中心",
            "formal_workflow_started": True,
            "evidence_gate_status": "PASS",
            "intended_output": "内部分析",
            "internal_report_generated": True,
            "department_results": departments,
        },
    )
    assert ledger["status"] == "PASS"
    assert ledger["missing_departments"] == []
    assert ledger["department_event_count"] == 6
    assert ledger["allows_external_delivery"] is False


def test_summarize_case_flow_ledgers_counts_statuses():
    summary = summarize_case_flow_ledgers([
        {"status": "BLOCK"},
        {"status": "ACTION_REQUIRED"},
        {"status": "PASS"},
        {"status": "BLOCK"},
    ])
    assert summary["ledger_count"] == 4
    assert summary["blocked_count"] == 2
    assert summary["action_required_count"] == 1
    assert summary["pass_count"] == 1
    assert summary["agi_completion_claim"] is False
