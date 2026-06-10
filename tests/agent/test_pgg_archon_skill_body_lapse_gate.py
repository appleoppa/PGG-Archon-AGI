"""Test the EmbodiSkill-inspired skill_body_lapse_separation_gate."""
from __future__ import annotations

from agent.pgg_archon_evolution_pattern_gates import skill_body_lapse_separation_gate


def _pass_packet() -> dict[str, object]:
    return {
        "skill_body_current": "original skill body",
        "skill_body_proposed_change": "fix error handling",
        "failure_trajectories": ["trajectory1", "trajectory2"],
        "evidence_type": "skill_changing",
        "change_classification": "skill_body_fix",
    }


def test_skill_body_fix_passes() -> None:
    ev = skill_body_lapse_separation_gate(_pass_packet())
    assert ev["status"] == "PASS"
    assert ev["embodiskill_inspired"] is True


def test_execution_lapse_preserve_without_body_change_passes() -> None:
    packet = dict(_pass_packet())
    packet["evidence_type"] = "execution_lapse"
    packet["change_classification"] = "execution_lapse_preserve"
    packet["skill_body_proposed_change"] = ""  # No body change for lapse
    ev = skill_body_lapse_separation_gate(packet)
    assert ev["status"] == "PASS"


def test_execution_lapse_with_body_change_warns() -> None:
    packet = dict(_pass_packet())
    packet["evidence_type"] = "execution_lapse"
    packet["change_classification"] = "execution_lapse_preserve"
    # Still has a proposed change → warning
    ev = skill_body_lapse_separation_gate(packet)
    assert ev["status"] == "WATCH"
    assert "execution_lapse_with_proposed_body_change_contradiction" in ev["warnings"]


def test_invalid_classification_blocks() -> None:
    packet = dict(_pass_packet())
    packet["change_classification"] = "bad"
    ev = skill_body_lapse_separation_gate(packet)
    assert ev["status"] == "BLOCK"
