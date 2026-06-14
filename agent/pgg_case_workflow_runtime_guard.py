"""Runtime guard for PGG legal case workflow start instructions.

This module turns a user instruction such as "启动办案程序" into a mandatory
pre-flight plan injected into the main conversation before the model answers.
It is intentionally conservative: it does not open cases, assign numbers, read
case files, or deliver legal work product. It only makes the workflow gate
visible to the orchestrator at the real conversation entry point.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping

from agent.pgg_case_workflow_entry import plan_case_workflow_entry

_START_TRIGGERS = ("启动办案程序", "开始办案", "执行办案", "进入办案流程")
_CASE_ID_RE = re.compile(r"PGG-[A-Z]+-\d{8}-\d{3}")
_EXTERNAL_ARBITRATION_RE = re.compile(r"（?\d{4}）?[^\n，。；;]{0,8}(?:信仲|仲裁)[^\n，。；;]{0,12}\d+号")
_DEFAULT_AUDIT_PATH = "~/.hermes/workspace/case_workflow_guard/runtime_guard.jsonl"


def has_case_start_trigger(text: Any) -> bool:
    """Return True when text looks like a legal case workflow start request."""
    if not isinstance(text, str):
        return False
    return any(token in text for token in _START_TRIGGERS)


def infer_case_state_from_instruction(text: str) -> dict[str, Any]:
    """Infer only safe aggregate workflow fields from the user instruction.

    The inference is intentionally minimal and never reads case files. Missing
    fields default to the safest gate posture so the orchestrator must either
    call the case-management center or supply verified state.
    """
    state: dict[str, Any] = {
        "formal_workflow_started": False,
        "evidence_gate_status": "UNKNOWN",
        "internal_report_generated": False,
    }
    pgg_match = _CASE_ID_RE.search(text)
    if pgg_match:
        state["case_id"] = pgg_match.group(0)
        state["case_id_generated_by"] = "案件管理中心"
    else:
        external_match = _EXTERNAL_ARBITRATION_RE.search(text)
        if external_match:
            state["case_id"] = external_match.group(0)
            state["case_id_generated_by"] = "外部案号"
    if any(word in text for word in ("正式", "终版", "对外交付", "律师函", "代理意见", "起诉状", "仲裁申请")):
        state["intended_output"] = text[:200]
    return state


def build_case_workflow_runtime_guard(
    user_instruction: str,
    case_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the mandatory runtime guard payload for a case workflow turn."""
    state = infer_case_state_from_instruction(user_instruction)
    if case_state:
        state.update(dict(case_state))
    plan = plan_case_workflow_entry(user_instruction, state)
    injection = (
        "【PGG办案流程强制前置门禁】\n"
        "检测到用户正在触发正式办案流程。你必须先执行以下边界，不能把材料初筛说成正式办案完成：\n"
        "1. 若 preflight 为 BLOCK/HOLD，只能输出内部流程计划、补证清单或门禁结论，不得输出正式/终版/对外交付法律文书。\n"
        "2. 若未有案件管理中心生成的 PGG 内部案号，必须先要求/规划案件管理中心编号，外部法院/仲裁案号不能替代内部案号。\n"
        "3. 若 formal_workflow_started 为 false，必须先规划正式部门流转：案件管理中心、标准任务包、部门并行、证据门禁、内部报告。\n"
        "4. 若证据门禁不是 PASS，法律依据/类案未实检，只能标注为内部初核方向。\n"
        "5. 回复中必须明确状态：中枢预审、正式流程已启动、后补启动、HOLD、BLOCK、可内部继续、可对外交付。\n"
        f"门禁计划JSON：{json.dumps(plan, ensure_ascii=False, sort_keys=True)}"
    )
    return {
        "schema": "PGGCaseWorkflowRuntimeGuard/v1",
        "triggered": True,
        "side_effects": "system_prompt_injection_and_optional_audit",
        "plan": plan,
        "system_injection": injection,
    }


def _audit_path() -> Path:
    return Path(os.environ.get("PGG_CASE_WORKFLOW_GUARD_AUDIT", _DEFAULT_AUDIT_PATH)).expanduser()


def persist_case_workflow_guard_audit(payload: Mapping[str, Any], *, session_id: str | None = None) -> None:
    """Append a low-sensitive aggregate audit record for runtime guard activation."""
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "PGGCaseWorkflowRuntimeGuardAudit/v1",
        "ts": time.time(),
        "session_id": session_id or "",
        "triggered": bool(payload.get("triggered")),
        "plan_status": ((payload.get("plan") or {}).get("status") if isinstance(payload.get("plan"), Mapping) else None),
        "preflight_status": (((payload.get("plan") or {}).get("preflight") or {}).get("status") if isinstance(payload.get("plan"), Mapping) else None),
        "issue_codes": [
            str(issue.get("code"))
            for issue in ((((payload.get("plan") or {}).get("preflight") or {}).get("issues") or []) if isinstance(payload.get("plan"), Mapping) else [])
            if isinstance(issue, Mapping)
        ],
        "action_count": int(((payload.get("plan") or {}).get("action_count") or 0) if isinstance(payload.get("plan"), Mapping) else 0),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def maybe_build_case_workflow_runtime_guard(
    user_instruction: Any,
    *,
    session_id: str | None = None,
    persist_audit: bool = True,
) -> dict[str, Any] | None:
    """Return a guard payload when the current turn starts a legal case workflow."""
    if not has_case_start_trigger(user_instruction):
        return None
    payload = build_case_workflow_runtime_guard(str(user_instruction))
    if persist_audit:
        try:
            persist_case_workflow_guard_audit(payload, session_id=session_id)
        except Exception:
            # Guard injection must not break normal conversation if audit storage fails.
            pass
    return payload


__all__ = [
    "has_case_start_trigger",
    "infer_case_state_from_instruction",
    "build_case_workflow_runtime_guard",
    "persist_case_workflow_guard_audit",
    "maybe_build_case_workflow_runtime_guard",
]
