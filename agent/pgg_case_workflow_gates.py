"""Pre-flight gates for PGG legal case workflow.

These pure functions convert lessons from real cases into machine-checkable
blocks/warnings before a draft is treated as formal or externally deliverable.
They do not read raw case files, mutate case archives, or perform delivery.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

_CASE_ID_RE = re.compile(r"^PGG-[A-Z]+-\d{8}-\d{3}$")
_START_TRIGGERS = ("启动办案程序", "开始办案", "执行办案", "进入办案流程")
_FINAL_WORDS = ("正式", "终版", "定稿", "对外交付", "发出", "律师函", "正式函件")


@dataclass(frozen=True)
class CaseWorkflowGateIssue:
    code: str
    severity: str
    message: str
    intercept_method: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "intercept_method": self.intercept_method,
        }


def _text(payload: Mapping[str, Any], key: str) -> str:
    return str(payload.get(key) or "")


def _seq(payload: Mapping[str, Any], key: str) -> Sequence[Any]:
    value = payload.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _has_any(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def evaluate_case_workflow_preflight(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate case workflow pre-flight gates.

    Expected safe aggregate fields include:
    - user_instruction
    - case_id
    - case_id_generated_by
    - formal_workflow_started
    - department_results: [{department, status}]
    - amount_versions / amount_delta_explained
    - evidence_gate_status
    - intended_output
    - internal_report_generated
    """
    instruction = _text(payload, "user_instruction")
    case_id = _text(payload, "case_id")
    case_id_generated_by = _text(payload, "case_id_generated_by")
    formal_workflow_started = bool(payload.get("formal_workflow_started"))
    department_results = _seq(payload, "department_results")
    amount_versions = _seq(payload, "amount_versions")
    amount_delta_explained = bool(payload.get("amount_delta_explained"))
    evidence_gate_status = _text(payload, "evidence_gate_status").upper()
    intended_output = _text(payload, "intended_output")
    internal_report_generated = bool(payload.get("internal_report_generated"))

    issues: list[CaseWorkflowGateIssue] = []

    if _has_any(instruction, _START_TRIGGERS) and not formal_workflow_started:
        issues.append(CaseWorkflowGateIssue(
            "case_start_trigger_not_formalized",
            "BLOCK",
            "用户触发启动办案程序后，必须启动案件管理中心编号和正式部门流程，不能降级为中枢初筛。",
            "pre_case_opening_guard:start_formal_workflow",
        ))

    if case_id and (not _CASE_ID_RE.match(case_id) or case_id_generated_by != "案件管理中心"):
        issues.append(CaseWorkflowGateIssue(
            "case_number_not_authorized_by_case_management",
            "BLOCK",
            "正式案号必须符合 PGG-{类型}-{日期}-{序号}，且只能由案件管理中心生成。",
            "pre_case_opening_guard:block_unauthorized_case_id",
        ))

    for result in department_results:
        if not isinstance(result, Mapping):
            continue
        status = str(result.get("status") or "").upper()
        exception_labeled = bool(result.get("exception_labeled"))
        if status in {"TIMEOUT", "ERROR", "FAILED"} and not exception_labeled:
            issues.append(CaseWorkflowGateIssue(
                "department_exception_without_label",
                "BLOCK",
                "部门调用失败、超时或异常时必须标注异常，不能写成已完成。",
                "department_gate:require_exception_label",
            ))

    if len(amount_versions) > 1 and not amount_delta_explained:
        issues.append(CaseWorkflowGateIssue(
            "amount_versions_without_closure",
            "HOLD",
            "金额出现多个版本或差额时，必须解释差额来源并形成金额闭合表。",
            "amount_gate:require_amount_closure",
        ))

    wants_final = _has_any(intended_output, _FINAL_WORDS)
    evidence_hold = evidence_gate_status in {"HOLD", "BLOCK", "UNKNOWN", ""}
    if wants_final and evidence_hold:
        issues.append(CaseWorkflowGateIssue(
            "formal_delivery_with_evidence_gate_hold",
            "BLOCK",
            "证据门禁未通过时，不得输出正式、终版或可对外交付文件。",
            "delivery_gate:block_formal_output_until_evidence_pass",
        ))

    if evidence_hold and not internal_report_generated:
        issues.append(CaseWorkflowGateIssue(
            "delivery_blocked_without_internal_report",
            "BLOCK",
            "不能对外交付时，必须生成内部办案流程报告，说明过程、结果、风险和下一步。",
            "case_close_guard:internal_report_required",
        ))

    severities = {issue.severity for issue in issues}
    if "BLOCK" in severities:
        status = "BLOCK"
    elif "HOLD" in severities:
        status = "HOLD"
    else:
        status = "PASS"
    return {
        "schema": "PGGCaseWorkflowPreflightGate/v1",
        "status": status,
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
        "side_effects": "pure_gate",
        "allows_external_delivery": status == "PASS" and not evidence_hold,
    }


def build_case_workflow_gate_from_runtimeos_status(status: Mapping[str, Any]) -> dict[str, Any]:
    """Build an aggregate-only case workflow gate for PGG Archon autonomy status.

    This bridges legal case practice into runtime visibility without reading raw
    case files, mutating case archives, calling departments, or delivering any
    legal output.
    """
    source = status.get("case_workflow_event")
    if not isinstance(source, Mapping):
        source = status.get("latest_case_workflow_event")
    if not isinstance(source, Mapping):
        return {
            "schema": "PGGCaseWorkflowRuntimeGate/v1",
            "status": "NO_EVENT",
            "preflight": None,
            "case_event_present": False,
            "allows_external_delivery": False,
            "side_effects": "read_only_report",
            "boundary": "No legal case files are read; this gate only evaluates sanitized aggregate event fields.",
        }

    preflight = evaluate_case_workflow_preflight(source)
    return {
        "schema": "PGGCaseWorkflowRuntimeGate/v1",
        "status": preflight["status"],
        "preflight": preflight,
        "case_event_present": True,
        "issue_count": preflight["issue_count"],
        "allows_external_delivery": preflight["allows_external_delivery"],
        "side_effects": "read_only_report",
        "boundary": "Aggregate-only legal workflow gate; not a substitute for department execution or legal-basis verification.",
    }


__all__ = [
    "CaseWorkflowGateIssue",
    "evaluate_case_workflow_preflight",
    "build_case_workflow_gate_from_runtimeos_status",
]
