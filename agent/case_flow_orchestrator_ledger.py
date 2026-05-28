"""Case-flow orchestrator ledger for PGG legal workflows.

The ledger reconciles sanitized case workflow plans, department statuses,
preflight gates, and delivery state into an auditable event stream. It does not
create case numbers, call departments, read raw case files, or deliver legal
work product.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from agent.pgg_case_workflow_entry import plan_case_workflow_entry
from agent.pgg_case_workflow_gates import evaluate_case_workflow_preflight

DEFAULT_LEDGER_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/case-flow-ledgers")
REQUIRED_DEPARTMENTS = (
    "案件管理中心",
    "证据管理部",
    "主办部门",
    "律法支持部",
    "案件推演部",
    "智脑知识部",
)
_TERMINAL_OK = {"PASS", "DONE", "COMPLETED", "OK"}
_TERMINAL_BAD = {"TIMEOUT", "ERROR", "FAILED", "BLOCK"}


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _safe_text(value: Any) -> str:
    return str(value or "")[:300]


@dataclass(frozen=True)
class CaseFlowLedgerEvent:
    event_type: str
    owner: str
    status: str
    action: str
    required: bool
    exception_labeled: bool
    evidence_hash: str | None
    remediation: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "owner": self.owner,
            "status": self.status,
            "action": self.action,
            "required": self.required,
            "exception_labeled": self.exception_labeled,
            "evidence_hash": self.evidence_hash,
            "remediation": self.remediation,
        }


def _department_event(raw: Mapping[str, Any]) -> CaseFlowLedgerEvent:
    owner = _safe_text(raw.get("department") or raw.get("owner") or "UNKNOWN")
    status = _safe_text(raw.get("status") or "UNKNOWN").upper()
    exception_labeled = bool(raw.get("exception_labeled"))
    remediation = None
    if status in _TERMINAL_BAD and not exception_labeled:
        remediation = "mark_department_exception_and_retry_or_compensate"
    elif status in _TERMINAL_BAD:
        remediation = "retry_or_compensate_with_exception_label"
    elif status not in _TERMINAL_OK:
        remediation = "await_department_completion_or_mark_exception"
    return CaseFlowLedgerEvent(
        event_type="department_status",
        owner=owner,
        status=status,
        action=_safe_text(raw.get("action") or "department_work"),
        required=bool(raw.get("required", True)),
        exception_labeled=exception_labeled,
        evidence_hash=_safe_text(raw.get("evidence_hash")) or None,
        remediation=remediation,
    )


def _action_event(raw: Mapping[str, Any]) -> CaseFlowLedgerEvent:
    return CaseFlowLedgerEvent(
        event_type="required_action",
        owner=_safe_text(raw.get("owner") or "苹果中枢"),
        status="ACTION_REQUIRED",
        action=_safe_text(raw.get("action") or "unknown_action"),
        required=bool(raw.get("required", True)),
        exception_labeled=False,
        evidence_hash=None,
        remediation=_safe_text(raw.get("completion_standard")) or None,
    )


def build_case_flow_orchestrator_ledger(
    user_instruction: str,
    case_state: Mapping[str, Any] | None = None,
    *,
    write_ledger: bool = False,
    ledger_dir: str | Path = DEFAULT_LEDGER_DIR,
) -> dict[str, Any]:
    state = dict(case_state or {})
    state.setdefault("user_instruction", user_instruction)
    preflight = evaluate_case_workflow_preflight(state)
    entry_plan = plan_case_workflow_entry(user_instruction, state)

    department_results = [_department_event(item).to_dict() for item in _as_sequence(state.get("department_results")) if isinstance(item, Mapping)]
    action_events = [_action_event(item).to_dict() for item in _as_sequence(entry_plan.get("actions")) if isinstance(item, Mapping)]
    present_departments = {event["owner"] for event in department_results}
    missing_departments = [dept for dept in REQUIRED_DEPARTMENTS if dept not in present_departments]
    blocking_events = [event for event in department_results if event["status"] in _TERMINAL_BAD and not event["exception_labeled"]]

    if preflight.get("status") == "BLOCK" or blocking_events:
        status = "BLOCK"
    elif preflight.get("status") == "HOLD" or action_events or missing_departments:
        status = "ACTION_REQUIRED"
    else:
        status = "PASS"

    delivery_intent = any(token in str(state.get("intended_output") or "") for token in ("正式", "终版", "定稿", "对外交付", "发出", "律师函", "正式函件"))
    ledger = {
        "schema": "PGGCaseFlowOrchestratorLedger/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "case_id": state.get("case_id") or "UNKNOWN-CASE",
        "user_instruction_hash": hashlib.sha256(user_instruction.encode("utf-8")).hexdigest(),
        "status": status,
        "preflight_status": preflight.get("status"),
        "preflight_issue_count": preflight.get("issue_count"),
        "entry_action_count": entry_plan.get("action_count"),
        "department_event_count": len(department_results),
        "missing_departments": missing_departments,
        "blocking_department_event_count": len(blocking_events),
        "events": [*department_results, *action_events],
        "allows_external_delivery": bool(preflight.get("allows_external_delivery")) and status == "PASS" and delivery_intent,
        "safe_to_continue_internal_work": bool(entry_plan.get("safe_to_continue_internal_work")),
        "side_effects": "ledger_write" if write_ledger else "read_only_plan",
        "boundary": "Sanitized aggregate ledger only; no department is called and no legal deliverable is generated.",
        "agi_completion_claim": False,
    }
    ledger["ledger_hash"] = _sha256_obj(ledger)
    if write_ledger:
        out_dir = Path(ledger_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        case_id = str(ledger["case_id"]).replace("/", "_")[:80]
        out = out_dir / f"{int(time.time())}_{case_id}_case_flow_ledger.json"
        out.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        ledger["ledger_path"] = str(out)
    return ledger


def summarize_case_flow_ledgers(ledgers: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in ledgers]
    status_counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema": "PGGCaseFlowLedgerSummary/v1",
        "ledger_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "blocked_count": status_counts.get("BLOCK", 0),
        "action_required_count": status_counts.get("ACTION_REQUIRED", 0),
        "pass_count": status_counts.get("PASS", 0),
        "agi_completion_claim": False,
    }


__all__ = ["build_case_flow_orchestrator_ledger", "summarize_case_flow_ledgers"]
