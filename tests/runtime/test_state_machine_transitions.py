from __future__ import annotations

import pytest

from runtime.state_machine.validator import StateTransitionError, validate_transition


def test_plan_ready_when_dependencies_satisfied():
    result = validate_transition("pending", "plan", {"dependencies_satisfied": True})
    assert result["schema"] == "ApexRuntimeOSTaskTransition/v1"
    assert result["next_state"] == "ready"
    assert result["emitted_event"] == "task_ready"
    assert result["side_effects"] == "read_only_report"


def test_block_unblock_cycle_requires_evidence():
    blocked = validate_transition("running", "block", {"blocker_recorded": True})
    assert blocked["next_state"] == "blocked"
    with pytest.raises(StateTransitionError, match="guard not satisfied"):
        validate_transition("blocked", "unblock", {"blocker_resolved": True, "dependencies_satisfied": False})
    unblocked = validate_transition("blocked", "unblock", {"blocker_resolved": True, "dependencies_satisfied": True})
    assert unblocked["next_state"] == "ready"


def test_illegal_transition_rejected():
    with pytest.raises(StateTransitionError, match="not allowed"):
        validate_transition("pending", "submit", {"output_attached": True})


def test_review_pass_requires_verification():
    with pytest.raises(StateTransitionError, match="guard not satisfied"):
        validate_transition("review", "review_pass", {"verification_passed": False})
    result = validate_transition("review", "review_pass", {"verification_passed": True})
    assert result["next_state"] == "done"
