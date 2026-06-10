"""Tests for internal evolution pattern gates."""

from __future__ import annotations

from typing import Any

from agent.pgg_archon_evolution_pattern_gates import (
    artifact_first_gate,
    evaluate_evolution_pattern_gates,
    harmrate_growth_gate,
    resource_lineage_gate,
    skill_body_lapse_separation_gate,
    skill_trajectory_gate,
)


def _pass_packet() -> dict[str, Any]:
    return {
        "resource_lineage": {
            "resource_registry": "registry.json",
            "resource_types": ["PROMPT", "TOOL", "AGENT", "MEM"],
            "fixed_objective_tests": "pytest",
            "evolution_loop": "SEPL",
            "lineage_log": "lineage.jsonl",
            "persistence_path": "state.json",
            "summary_readback": "summary",
        },
        "artifact_first": {
            "idea_or_source_note": "note.md",
            "plan_json": "plan.json",
            "baseline_or_action": "baseline",
            "metrics_json": '{"accuracy":0.5}',
            "report_md": "report.md",
        },
        "skill_trajectory": {
            "strategy_explorer": "k strategies",
            "task_execution_traces": ["t1", "t2"],
            "success_failure_comparison": "delta",
            "targeted_patch": "patch",
            "independent_audit": "reviewer",
            "rollback_or_versioning": "v1",
        },
        "skill_body_lapse": {
            "skill_body_current": "original skill body",
            "skill_body_proposed_change": "fix error handling",
            "failure_trajectories": ["t1", "t2"],
            "evidence_type": "skill_changing",
            "change_classification": "skill_body_fix",
        },
        "declarative_spec": {
            "spec_format": "yaml",
            "typed_steps": ["step1", "step2"],
            "explicit_state": "state.json",
            "module_reuse": True,
            "sandbox_rollback": True,
        },
        "population_search": {
            "families": [{"name": "a"}, {"name": "b"}],
            "selection_strategy": "fitness",
            "stagnation_detection": {"max_family_failures": 3},
            "novelty_injection": True,
            "candidate_hypotheses": True,
            "population_persistence": True,
        },
        "morphogenetic_acceptance": {
            "delta_error": -0.3,
            "delta_complexity": 0.05,
            "complexity_beta": 1.0,
            "refractory_rounds_remaining": 0,
            "temperature": 1.0,
            "invariant_breach": False,
            "refinement_preserves_behavior": True,
        },
        "harmrate_growth": {
            "harmrate": 0.1,
            "verification": "tests",
            "sandbox_test": "sandbox",
            "rollback_plan": "rollback",
            "change_scope": "local",
        },
    }


def test_resource_lineage_gate_passes_and_blocks_missing() -> None:
    assert resource_lineage_gate(_pass_packet()["resource_lineage"])["status"] == "PASS"
    assert resource_lineage_gate({})["status"] == "BLOCK"


def test_artifact_first_gate_requires_valid_metrics_json() -> None:
    assert artifact_first_gate(_pass_packet()["artifact_first"])["status"] == "PASS"
    bad = dict(_pass_packet()["artifact_first"])
    bad["metrics_json"] = "not-json"
    out = artifact_first_gate(bad)
    assert out["status"] == "BLOCK"
    assert "metrics_json_invalid" in out["errors"]


def test_skill_trajectory_gate_blocks_full_rewrite_and_self_audit() -> None:
    assert skill_trajectory_gate(_pass_packet()["skill_trajectory"])["status"] == "PASS"
    bad = dict(_pass_packet()["skill_trajectory"])
    bad["full_rewrite"] = True
    bad["independent_audit"] = "self_only"
    out = skill_trajectory_gate(bad)
    assert out["status"] == "BLOCK"
    assert "full_rewrite_not_allowed_without_separate_review" in out["errors"]
    assert "independent_audit_cannot_be_self_only" in out["errors"]


def test_harmrate_growth_gate_blocks_threshold_and_external_claim() -> None:
    assert harmrate_growth_gate(_pass_packet()["harmrate_growth"])["status"] == "PASS"
    bad = dict(_pass_packet()["harmrate_growth"])
    bad["harmrate"] = 0.34
    bad["external_authority_claim"] = True
    out = harmrate_growth_gate(bad)
    assert out["status"] == "BLOCK"
    assert "harmrate_at_or_above_threshold" in out["errors"]
    assert "external_authority_claim_not_allowed" in out["errors"]


def test_population_search_gate_passes_with_multiple_families() -> None:
    from agent.pgg_archon_evolution_pattern_gates import population_search_gate
    ev = population_search_gate({
        "families": [{"name": "a"}, {"name": "b"}],
        "selection_strategy": "fitness",
        "stagnation_detection": {"max_family_failures": 3},
        "novelty_injection": True,
        "candidate_hypotheses": True,
        "population_persistence": True,
    })
    assert ev["status"] == "PASS"
    assert ev["pievo_inspired"] is True


def test_population_search_gate_single_family_warns() -> None:
    from agent.pgg_archon_evolution_pattern_gates import population_search_gate
    ev = population_search_gate({
        "families": [{"name": "only_one"}],
        "selection_strategy": "fitness",
        "stagnation_detection": {"max_family_failures": 3},
    })
    assert ev["status"] == "WATCH"
    assert "less_than_2_families" in ev["warnings"]


def test_evaluate_all_gates_writes_output(tmp_path) -> None:
    out = evaluate_evolution_pattern_gates(_pass_packet(), output_dir=tmp_path)
    assert out["status"] == "PASS"
    assert out["blocked"] == []
    assert out["promotion_performed"] is False
    assert out["official_source_claim"] is False
    assert "output_path" in out
