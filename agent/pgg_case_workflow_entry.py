"""Case workflow entry planner that applies pre-flight gates before case work.

This module is the safe integration layer between a user instruction such as
"启动办案程序" and the formal PGG case workflow. It returns machine-readable next
actions instead of performing irreversible operations.
"""
from __future__ import annotations

from typing import Any, Mapping

from agent.pgg_case_workflow_gates import evaluate_case_workflow_preflight

_START_TRIGGERS = ("启动办案程序", "开始办案", "执行办案", "进入办案流程")


def _has_start_trigger(text: str) -> bool:
    return any(token in text for token in _START_TRIGGERS)


def plan_case_workflow_entry(user_instruction: str, case_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Plan safe next actions for a legal case workflow entry.

    The planner does not create folders, assign case numbers, or deliver legal
    work product. It tells the orchestrator what must happen next and blocks
    unsafe shortcuts exposed by real case practice.
    """
    state = dict(case_state or {})
    state.setdefault("user_instruction", user_instruction)
    preflight = evaluate_case_workflow_preflight(state)
    actions: list[dict[str, Any]] = []

    if _has_start_trigger(user_instruction) and not state.get("formal_workflow_started"):
        actions.extend([
            {
                "action": "request_case_management_numbering",
                "owner": "案件管理中心",
                "required": True,
                "completion_standard": "返回 PGG 正式案号、案卷目录、台账路径",
            },
            {
                "action": "create_standard_case_task_pack",
                "owner": "苹果中枢",
                "required": True,
                "completion_standard": "生成标准案件任务包、案件项目计划卡、并行调度表",
            },
            {
                "action": "dispatch_parallel_departments",
                "owner": "苹果中枢",
                "required": True,
                "completion_standard": "证据管理部、主办部门、律法支持部、案件推演部、智脑知识部均有真实回收状态",
            },
        ])

    issue_codes = {issue["code"] for issue in preflight.get("issues", [])}
    if "amount_versions_without_closure" in issue_codes:
        actions.append({
            "action": "build_amount_closure_table",
            "owner": "主办部门/中枢",
            "required": True,
            "completion_standard": "列明总额、已付、扣减、待付、差额来源；不闭合不得生成正式函件",
        })
    if "formal_delivery_with_evidence_gate_hold" in issue_codes:
        actions.append({
            "action": "downgrade_to_internal_draft",
            "owner": "苹果中枢",
            "required": True,
            "completion_standard": "输出标注为内部预分析/待补证稿，不得标注正式或对外交付",
        })
    if "delivery_blocked_without_internal_report" in issue_codes:
        actions.append({
            "action": "generate_internal_case_process_report",
            "owner": "苹果中枢",
            "required": True,
            "completion_standard": "包含办案过程、部门参与、初步结果、风险、门禁结论、下一步，并只同步最终报告到桌面",
        })
    if "department_exception_without_label" in issue_codes:
        actions.append({
            "action": "mark_department_exception_and_retry_or_compensate",
            "owner": "苹果中枢",
            "required": True,
            "completion_standard": "区分真实部门回收、超时异常和中枢补救稿",
        })
    if "case_number_not_authorized_by_case_management" in issue_codes:
        actions.append({
            "action": "void_unauthorized_case_number",
            "owner": "案件管理中心",
            "required": True,
            "completion_standard": "废止中枢临时号，补正案件管理中心正式 PGG 编号",
        })

    safe_to_proceed = preflight.get("status") == "PASS" or bool(actions)
    return {
        "schema": "PGGCaseWorkflowEntryPlan/v1",
        "status": "ACTION_REQUIRED" if actions else preflight.get("status", "UNKNOWN"),
        "preflight": preflight,
        "actions": actions,
        "action_count": len(actions),
        "safe_to_continue_internal_work": safe_to_proceed,
        "allows_external_delivery": bool(preflight.get("allows_external_delivery")) and not actions,
        "side_effects": "pure_plan",
    }


__all__ = ["plan_case_workflow_entry"]
