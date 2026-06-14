"""Tests for internal evolution pattern gates."""

from __future__ import annotations

from typing import Any

from agent.pgg_archon_evolution_pattern_gates import (
    artifact_first_gate,
    coral_multi_agent_parallel_gate,
    evaluate_evolution_pattern_gates,
    agentspex_full_harness_gate,
    gepa_prompt_optimizer_gate,
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
        "gepa_prompt_optimizer": {
            "baseline_prompt_or_program": "prompt_v1",
            "task_metric": "exact_match",
            "reflective_feedback": ["error cluster A", "fix instruction B"],
            "candidate_variants": ["v2", "v3", "v4"],
            "validation_split": "holdout.jsonl",
            "pareto_or_score_selection": "metric_then_complexity",
            "metric_readback": {"exact_match": 0.72},
            "rollback_or_versioning": "prompt_v1",
        },
        "coral_multi_agent_parallel": {
            "agent_population": ["researcher", "builder", "auditor"],
            "parallel_workspaces": ["wt_a", "wt_b", "wt_c"],
            "shared_objective": "reduce failing cases",
            "independent_experiments": ["exp_a", "exp_b"],
            "merge_selection_policy": "best_regression_delta",
            "cross_agent_audit": "auditor_reviews_builder",
            "conflict_resolution": "reject_conflicting_patch",
            "final_regression_gate": "pytest + gate",
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
        "agentspex_full_harness": {
            "spec_format": "yaml",
            "typed_steps": [
                {"id": "s1", "type": "load", "input": "case_material", "output": "state.material"},
                {"id": "s2", "type": "verify", "input": "state.material", "output": "state.evidence"},
                {"id": "s3", "type": "deliver", "input": "state.evidence", "output": "state.report"},
            ],
            "explicit_state": {"schema": "state.schema.json", "mutation_policy": "append_only_evidence"},
            "control_flow": {"sequence": ["s1", "s2", "s3"], "parallel": ["evidence", "law"], "join_policy": "all_pass"},
            "module_reuse": ["agent-cms", "dept-evidence-management", "dept-legal-support"],
            "sandbox": {"enabled": True, "workspace": "case_sandbox", "rollback": "restore checkpoint"},
            "tool_bindings": [
                {"name": "cms_case_guard", "permission": "read_write_case_index"},
                {"name": "case_trusted_workflow_gate", "permission": "read_only_verify"},
            ],
            "checkpoint_resume": {"enabled": True, "resume_key": "case_id+stage"},
            "verifier": {"gates": ["cms_validate", "trusted_workflow"], "success_criteria": "all hard gates pass"},
            "logger": {"evidence_path": "workspace/case/evidence", "manifest_key": "sample_agentspex_case"},
            "boundary": "internal spec gate only; no benchmark/full AGI claim",
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


def test_gepa_prompt_optimizer_gate_blocks_leakage_and_unverified_metric() -> None:
    assert gepa_prompt_optimizer_gate(_pass_packet()["gepa_prompt_optimizer"])["status"] == "PASS"
    bad = dict(_pass_packet()["gepa_prompt_optimizer"])
    bad["train_equals_validation"] = True
    bad["metric_improvement_claimed"] = True
    bad.pop("metric_readback", None)
    out = gepa_prompt_optimizer_gate(bad)
    assert out["status"] == "BLOCK"
    assert "train_validation_leakage" in out["errors"]
    assert "metric_improvement_claim_without_readback" in out["errors"]
    assert out["gepa_inspired"] is True


def test_coral_multi_agent_parallel_gate_blocks_shared_mutation() -> None:
    assert coral_multi_agent_parallel_gate(_pass_packet()["coral_multi_agent_parallel"])["status"] == "PASS"
    bad = dict(_pass_packet()["coral_multi_agent_parallel"])
    bad["shared_workspace_mutation"] = True
    bad["merge_without_regression"] = True
    bad["self_audit_only"] = True
    out = coral_multi_agent_parallel_gate(bad)
    assert out["status"] == "BLOCK"
    assert "shared_workspace_mutation_not_allowed" in out["errors"]
    assert "merge_without_regression_not_allowed" in out["errors"]
    assert "cross_agent_audit_cannot_be_self_only" in out["errors"]
    assert out["coral_inspired"] is True


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


def test_agentspex_full_harness_gate_passes_and_blocks_unsafe_claims() -> None:
    out = agentspex_full_harness_gate(_pass_packet()["agentspex_full_harness"])
    assert out["status"] == "PASS"
    assert out["agentspex_full_harness_inspired"] is True
    bad = dict(_pass_packet()["agentspex_full_harness"])
    bad["benchmark_claim"] = True
    bad["official_agentspex_parity_claim"] = True
    bad["full_agi_claim"] = True
    out = agentspex_full_harness_gate(bad)
    assert out["status"] == "BLOCK"
    assert "benchmark_claim_not_allowed_without_local_eval" in out["errors"]
    assert "official_agentspex_parity_claim_not_allowed" in out["errors"]
    assert "full_agi_claim_not_allowed" in out["errors"]


def test_agentspex_full_harness_gate_requires_parallel_join_policy() -> None:
    bad = dict(_pass_packet()["agentspex_full_harness"])
    bad["control_flow"] = {"parallel": ["a", "b"]}
    out = agentspex_full_harness_gate(bad)
    assert out["status"] == "BLOCK"
    assert "parallel_control_flow_requires_join_policy" in out["errors"]


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
