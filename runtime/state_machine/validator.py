"""APEX RuntimeOS task state transition validator.

This module is a low-risk control-plane asset derived from the desktop
"超级进化" materials.  It is intentionally deterministic and side-effect free:
it validates a requested task transition and returns a small report; it does not
modify kanban boards, files, memory, or external services.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

_DEFAULT_TRANSITIONS = Path(__file__).with_name("transitions.yaml")


class StateTransitionError(ValueError):
    """Raised when a requested state transition is invalid."""


@dataclass(frozen=True)
class TransitionResult:
    current_state: str
    event: str
    next_state: str
    emitted_event: str
    guard: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "schema": "ApexRuntimeOSTaskTransition/v1",
            "current_state": self.current_state,
            "event": self.event,
            "next_state": self.next_state,
            "emitted_event": self.emitted_event,
            "guard": self.guard,
            "side_effects": "read_only_report",
        }


def load_transition_table(path: Path | None = None) -> Dict[str, Any]:
    resolved = path or _DEFAULT_TRANSITIONS
    data = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise StateTransitionError("transition table must be a mapping")
    return data


def _as_state_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _guard_satisfied(guard: str, context: Mapping[str, Any]) -> bool:
    if guard == "dependencies_satisfied":
        return bool(context.get("dependencies_satisfied"))
    if guard == "blocker_recorded":
        return bool(context.get("blocker_recorded"))
    if guard == "blocker_resolved_and_dependencies_satisfied":
        return bool(context.get("blocker_resolved")) and bool(context.get("dependencies_satisfied"))
    if guard == "assignee_available":
        return bool(context.get("assignee_available"))
    if guard == "output_attached":
        return bool(context.get("output_attached"))
    if guard == "verification_passed":
        return bool(context.get("verification_passed"))
    if guard == "verification_failed":
        return bool(context.get("verification_failed"))
    if guard == "retry_budget_available":
        return bool(context.get("retry_budget_available"))
    if guard == "cancellation_authorized":
        return bool(context.get("cancellation_authorized"))
    return False


def validate_transition(
    current_state: str,
    event: str,
    context: Mapping[str, Any] | None = None,
    *,
    table_path: Path | None = None,
) -> Dict[str, str]:
    """Validate a task transition and return the next-state report.

    Raises StateTransitionError for unknown states/events, illegal transitions,
    or unsatisfied guards.
    """
    table = load_transition_table(table_path)
    states = {str(item) for item in table.get("states", [])}
    events = table.get("events") if isinstance(table.get("events"), dict) else {}
    state = str(current_state)
    event_name = str(event)
    ctx = context or {}
    if state not in states:
        raise StateTransitionError(f"unknown state: {state}")
    if event_name not in events:
        raise StateTransitionError(f"unknown event: {event_name}")
    rule = events[event_name]
    if not isinstance(rule, dict):
        raise StateTransitionError(f"malformed event rule: {event_name}")
    allowed_from = _as_state_list(rule.get("from"))
    if state not in allowed_from:
        raise StateTransitionError(f"event {event_name} is not allowed from {state}")
    guard = str(rule.get("guard") or "")
    if not _guard_satisfied(guard, ctx):
        raise StateTransitionError(f"guard not satisfied: {guard}")
    result = TransitionResult(
        current_state=state,
        event=event_name,
        next_state=str(rule.get("to")),
        emitted_event=str(rule.get("emits")),
        guard=guard,
    )
    return result.as_dict()


__all__ = [
    "StateTransitionError",
    "TransitionResult",
    "load_transition_table",
    "validate_transition",
]
