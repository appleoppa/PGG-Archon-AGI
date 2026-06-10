"""PGG internal evolution-pattern gates distilled from Xuanji-route GitHub factors.

Boundary:
- PGG internal structural gates only;
- no network, no LLM calls, no external code execution/copy;
- no GeneDB promotion and no official-source claim;
- does not prove AGI/T5/ASI capability.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

BOUNDARY = "internal_evolution_pattern_gates; no promotion; no external code copy; no AGI/T5/ASI claim"


def _safe_exp(x: float) -> float:
    """Safely compute exp(x), clamped to avoid overflow."""
    import math
    try:
        return math.exp(max(-100.0, min(100.0, x)))
    except (OverflowError, ValueError):
        return float('inf') if x > 0 else 0.0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _has(obj: Mapping[str, Any], key: str) -> bool:
    value = obj.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(str(value or "").strip())


def resource_lineage_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Check self-evolution packets have registry, objective, loop, lineage, persistence."""
    required = [
        "resource_registry",
        "resource_types",
        "fixed_objective_tests",
        "evolution_loop",
        "lineage_log",
        "persistence_path",
        "summary_readback",
    ]
    missing = [field for field in required if not _has(packet, field)]
    resource_types = packet.get("resource_types") or []
    if isinstance(resource_types, str):
        resource_types = [x.strip() for x in resource_types.split(",") if x.strip()]
    warnings: list[str] = []
    if len(resource_types) < 3:
        warnings.append("resource_types_less_than_3")
    status = "PASS" if not missing else "BLOCK"
    return {
        "schema": "PGGResourceLineageGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "warnings": warnings,
        "boundary": BOUNDARY,
    }


def artifact_first_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Check benchmark/research task leaves plan/action/metrics/report artifacts."""
    required = ["idea_or_source_note", "plan_json", "baseline_or_action", "metrics_json", "report_md"]
    missing = [field for field in required if not _has(packet, field)]
    metrics = packet.get("metrics_json")
    errors: list[str] = []
    if _has(packet, "metrics_json") and isinstance(metrics, str):
        try:
            json.loads(metrics)
        except Exception:
            errors.append("metrics_json_invalid")
    status = "PASS" if not missing and not errors else "BLOCK"
    return {
        "schema": "PGGArtifactFirstGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "errors": errors,
        "boundary": BOUNDARY,
    }



def gepa_prompt_optimizer_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """GEPA-inspired: reflective prompt/program optimization with Pareto validation.

    Boundary: local structural gate only; no DSPy/GEPA execution, no official-source
    claim, no GeneDB promotion. It checks prompt evolution is metric-grounded rather
    than arbitrary rewrite.
    """
    required = [
        "baseline_prompt_or_program",
        "task_metric",
        "reflective_feedback",
        "candidate_variants",
        "validation_split",
        "pareto_or_score_selection",
        "rollback_or_versioning",
    ]
    missing = [field for field in required if not _has(packet, field)]
    errors: list[str] = []
    warnings: list[str] = []
    metrics: list[str] = []

    variants = packet.get("candidate_variants") or []
    if isinstance(variants, (list, tuple)):
        metrics.append(f"candidate_variants:{len(variants)}")
        if len(variants) < 2:
            warnings.append("less_than_2_candidate_variants")
    if packet.get("train_equals_validation") is True:
        errors.append("train_validation_leakage")
    if packet.get("metric_improvement_claimed") is True and not _has(packet, "metric_readback"):
        errors.append("metric_improvement_claim_without_readback")
    if packet.get("manual_prompt_rewrite_only") is True:
        warnings.append("manual_rewrite_without_reflective_search")
    if _has(packet, "pareto_or_score_selection"):
        metrics.append("has_selection_rule")
    if _has(packet, "reflective_feedback"):
        metrics.append("has_reflective_feedback")

    status = "PASS" if not missing and not errors else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGGEPAReflectivePromptOptimizerGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "gepa_inspired": True,
        "boundary": BOUNDARY,
    }


def coral_multi_agent_parallel_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """CORAL-inspired: autonomous multi-agent evolution with isolated workspaces.

    Boundary: local structural gate only; does not run CORAL and does not claim
    official implementation parity. It checks whether multi-agent evolution proposals
    are isolated, merged by evidence, and audited.
    """
    required = [
        "agent_population",
        "parallel_workspaces",
        "shared_objective",
        "independent_experiments",
        "merge_selection_policy",
        "cross_agent_audit",
        "conflict_resolution",
        "final_regression_gate",
    ]
    missing = [field for field in required if not _has(packet, field)]
    errors: list[str] = []
    warnings: list[str] = []
    metrics: list[str] = []

    agents = packet.get("agent_population") or []
    workspaces = packet.get("parallel_workspaces") or []
    if isinstance(agents, (list, tuple)):
        metrics.append(f"agents:{len(agents)}")
        if len(agents) < 2:
            warnings.append("less_than_2_agents")
    if isinstance(workspaces, (list, tuple)):
        metrics.append(f"workspaces:{len(workspaces)}")
        if len(workspaces) < 2:
            warnings.append("less_than_2_parallel_workspaces")
    if packet.get("shared_workspace_mutation") is True:
        errors.append("shared_workspace_mutation_not_allowed")
    if packet.get("merge_without_regression") is True:
        errors.append("merge_without_regression_not_allowed")
    if packet.get("self_audit_only") is True:
        errors.append("cross_agent_audit_cannot_be_self_only")
    if _has(packet, "merge_selection_policy"):
        metrics.append("has_merge_selection_policy")
    if _has(packet, "final_regression_gate"):
        metrics.append("has_final_regression_gate")

    status = "PASS" if not missing and not errors else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGCORALMultiAgentParallelGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "coral_inspired": True,
        "boundary": BOUNDARY,
    }


def skill_trajectory_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Check skill evolution has strategies, success/failure comparison, narrow patch, audit."""
    required = [
        "strategy_explorer",
        "task_execution_traces",
        "success_failure_comparison",
        "targeted_patch",
        "independent_audit",
        "rollback_or_versioning",
    ]
    missing = [field for field in required if not _has(packet, field)]
    errors: list[str] = []
    if packet.get("full_rewrite") is True:
        errors.append("full_rewrite_not_allowed_without_separate_review")
    if packet.get("independent_audit") == "self_only":
        errors.append("independent_audit_cannot_be_self_only")
    status = "PASS" if not missing and not errors else "BLOCK"
    return {
        "schema": "PGGSkillTrajectoryGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "errors": errors,
        "boundary": BOUNDARY,
    }


def harmrate_growth_gate(packet: Mapping[str, Any], *, threshold: float = 0.34) -> dict[str, Any]:
    """Check growth is thresholded, reversible, sandboxed, and user-confirmed when required."""
    harmrate = float(packet.get("harmrate", 1.0) or 0.0)
    required = ["verification", "sandbox_test", "rollback_plan", "change_scope"]
    missing = [field for field in required if not _has(packet, field)]
    errors: list[str] = []
    if harmrate >= threshold:
        errors.append("harmrate_at_or_above_threshold")
    if packet.get("external_authority_claim") is True:
        errors.append("external_authority_claim_not_allowed")
    if packet.get("production_or_security_change") is True and not _has(packet, "user_confirmation"):
        errors.append("production_or_security_change_requires_user_confirmation")
    status = "PASS" if not missing and not errors else "BLOCK"
    return {
        "schema": "PGGHarmRateGrowthGate/v1",
        "created_at": _now(),
        "status": status,
        "harmrate": harmrate,
        "threshold": threshold,
        "missing": missing,
        "errors": errors,
        "boundary": BOUNDARY,
    }


def skill_body_lapse_separation_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """EmbodiSkill-inspired: separate skill-body changes from execution-lapse preservation.

    A skill update must distinguish whether a failure is caused by incorrect skill content
    (skill-body issue → fix the body) or by the agent failing to follow valid guidance
    (execution lapse → preserve and reinforce existing guidance, do not rewrite body).
    """
    required = [
        "skill_body_current",
        "failure_trajectories",
        "evidence_type",
        "change_classification",
    ]
    optional = ["skill_body_proposed_change"]
    missing = [field for field in required if not _has(packet, field)]
    evidence_type = str(packet.get("evidence_type", "")).strip()
    change_classification = str(packet.get("change_classification", "")).strip()
    errors: list[str] = []
    warnings: list[str] = []
    if change_classification not in {"skill_body_fix", "execution_lapse_preserve", "mixed"}:
        errors.append(f"invalid_change_classification:{change_classification}")
    if evidence_type not in {"skill_changing", "execution_lapse", "both"}:
        errors.append(f"invalid_evidence_type:{evidence_type}")
    if change_classification == "execution_lapse_preserve" and _has(packet, "skill_body_proposed_change"):
        if str(packet.get("skill_body_proposed_change", "")).strip():
            warnings.append("execution_lapse_with_proposed_body_change_contradiction")
    status = "PASS" if not missing and not errors else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGSkillBodyLapseSeparationGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "errors": errors,
        "warnings": warnings,
        "boundary": BOUNDARY,
        "embodiskill_inspired": True,
    }


def morphogenetic_acceptance_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """OpenCOAT morphogenetic agent inspired: ΔF acceptance criterion.

    A structural evolution is accepted only when:
        ΔF = ΔError + β·ΔComplexity < 0

    This formalizes the acceptance check for evolutionary changes:
    - ΔError: change in task/prediction error (negative = improvement)
    - ΔComplexity: change in structural description length
    - β: complexity coefficient (temperature-dependent)
    - Refractory period prevents oscillation.
    """
    required = [
        "delta_error",
        "delta_complexity",
        "complexity_beta",
    ]
    missing = [field for field in required if not _has(packet, field)]
    warnings: list[str] = []
    metrics: list[str] = []
    delta_error = float(packet.get("delta_error", 0.0) or 0.0)
    delta_complexity = float(packet.get("delta_complexity", 0.0) or 0.0)
    beta = float(packet.get("complexity_beta", 1.0) or 1.0)
    refractory = int(packet.get("refractory_rounds_remaining", 0) or 0)
    delta_f = delta_error + beta * delta_complexity
    effective_temperature = float(packet.get("temperature", 1.0) or 1.0)
    rate = min(1.0, _safe_exp(-delta_f / effective_temperature)) if effective_temperature > 0 else 0.0

    errors: list[str] = []
    if refractory > 0:
        errors.append("refractory_rounds_remaining")
    if not missing and delta_f >= 0:
        errors.append("delta_f_not_negative")

    if _has(packet, "invariant_breach"):
        if packet.get("invariant_breach") is True:
            errors.append("invariant_breach")
    if _has(packet, "refinement_preserves_behavior") and packet.get("refinement_preserves_behavior") is False:
        errors.append("refinement_does_not_preserve_behavior")

    metrics.append(f"ΔF={delta_f:.4f}")
    metrics.append(f"rate={rate:.4f}")
    metrics.append(f"temperature={effective_temperature:.2f}")
    status = "PASS" if not missing and not errors else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGMorphogeneticAcceptanceGate/v1",
        "created_at": _now(),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "delta_f": delta_f,
        "acceptance_rate": rate,
        "opencoat_inspired": True,
        "opencat_inspired": True,  # backward-compatible typo alias
        "boundary": BOUNDARY,
    }


def population_search_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """pi-evo-research inspired: check candidate evolution uses population-guided search.

    Instead of single-path hill-climbing, maintain multiple candidate families
    with stagnation detection, novelty injection, and family diversity.
    """
    required = [
        "families",
        "selection_strategy",
        "stagnation_detection",
    ]
    metrics: list[str] = []
    warnings: list[str] = []
    missing = [field for field in required if not _has(packet, field)]
    families = packet.get("families") or []
    if isinstance(families, (list, tuple)):
        if len(families) < 2:
            warnings.append("less_than_2_families")
        names = [f.get("name", str(f))[:40] if isinstance(f, dict) else str(f)[:40] for f in families]
        if names:
            metrics.append(f"families:{','.join(names)}")
    stagnation = packet.get("stagnation_detection") or {}
    if isinstance(stagnation, dict):
        max_fail = stagnation.get("max_family_failures")
        if max_fail is not None:
            metrics.append(f"max_family_failures:{max_fail}")
    novelty = packet.get("novelty_injection")
    if novelty and _has(packet, "novelty_injection"):
        metrics.append("has_novelty_injection")
    if _has(packet, "candidate_hypotheses"):
        metrics.append("has_candidate_hypotheses")
    if _has(packet, "population_persistence"):
        metrics.append("has_population_persistence")
    status = "PASS" if not missing else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGPopulationSearchGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "warnings": warnings,
        "metrics": metrics,
        "pievo_inspired": True,
        "boundary": BOUNDARY,
    }



def agentspex_full_harness_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """AgentSPEX-inspired full harness spec gate.

    Checks whether a task spec is executable as a declarative workflow:
    typed steps, explicit state, control flow, module reuse, sandbox, tool bindings,
    checkpoint/resume, verifier/logger, state mutation audit, and boundary claims.

    Boundary: local structural validation only. It does not execute AgentSPEX, does not
    reproduce paper benchmarks, and does not claim official AgentSPEX parity.
    """
    required = [
        "spec_format",
        "typed_steps",
        "explicit_state",
        "control_flow",
        "module_reuse",
        "sandbox",
        "tool_bindings",
        "checkpoint_resume",
        "verifier",
        "logger",
        "boundary",
    ]
    missing = [field for field in required if not _has(packet, field)]
    errors: list[str] = []
    warnings: list[str] = []
    metrics: list[str] = []

    spec_format = str(packet.get("spec_format", "")).strip().lower()
    if spec_format and spec_format not in {"yaml", "json", "toml", "markdown"}:
        warnings.append(f"nonstandard_spec_format:{spec_format}")

    typed_steps = packet.get("typed_steps") or []
    if isinstance(typed_steps, (list, tuple)):
        metrics.append(f"typed_steps:{len(typed_steps)}")
        if len(typed_steps) < 3:
            warnings.append("less_than_3_typed_steps")
        for idx, step in enumerate(typed_steps):
            if not isinstance(step, Mapping):
                errors.append(f"typed_step_{idx}_not_mapping")
                continue
            for field in ("id", "type", "input", "output"):
                if not _has(step, field):
                    errors.append(f"typed_step_{idx}_missing_{field}")

    control_flow = packet.get("control_flow") or {}
    if isinstance(control_flow, Mapping):
        if not any(_has(control_flow, key) for key in ("sequence", "branch", "loop", "parallel", "join_policy")):
            warnings.append("control_flow_has_no_operator")
        if _has(control_flow, "parallel") and not _has(control_flow, "join_policy"):
            errors.append("parallel_control_flow_requires_join_policy")

    state = packet.get("explicit_state") or {}
    if isinstance(state, Mapping):
        if not _has(state, "schema"):
            errors.append("explicit_state_missing_schema")
        if not _has(state, "mutation_policy"):
            errors.append("explicit_state_missing_mutation_policy")

    sandbox = packet.get("sandbox") or {}
    if isinstance(sandbox, Mapping):
        if sandbox.get("enabled") is not True:
            errors.append("sandbox_not_enabled")
        if not _has(sandbox, "rollback"):
            errors.append("sandbox_missing_rollback")
        if sandbox.get("production_or_security_change") is True and not _has(packet, "user_authorization"):
            errors.append("production_or_security_change_requires_user_authorization")

    tools = packet.get("tool_bindings") or []
    if isinstance(tools, (list, tuple)):
        metrics.append(f"tool_bindings:{len(tools)}")
        if not tools:
            errors.append("no_tool_bindings")
        for idx, tool in enumerate(tools):
            if isinstance(tool, Mapping):
                if not _has(tool, "name"):
                    errors.append(f"tool_binding_{idx}_missing_name")
                if not _has(tool, "permission"):
                    errors.append(f"tool_binding_{idx}_missing_permission")

    checkpoint = packet.get("checkpoint_resume") or {}
    if isinstance(checkpoint, Mapping):
        if checkpoint.get("enabled") is not True:
            errors.append("checkpoint_resume_not_enabled")
        if not _has(checkpoint, "resume_key"):
            errors.append("checkpoint_resume_missing_resume_key")

    verifier = packet.get("verifier") or {}
    if isinstance(verifier, Mapping):
        if not _has(verifier, "gates"):
            errors.append("verifier_missing_gates")
        if not _has(verifier, "success_criteria"):
            errors.append("verifier_missing_success_criteria")

    logger = packet.get("logger") or {}
    if isinstance(logger, Mapping):
        if not _has(logger, "evidence_path"):
            errors.append("logger_missing_evidence_path")
        if not _has(logger, "manifest_key"):
            warnings.append("logger_missing_manifest_key")

    if packet.get("benchmark_claim") is True:
        errors.append("benchmark_claim_not_allowed_without_local_eval")
    if packet.get("official_agentspex_parity_claim") is True:
        errors.append("official_agentspex_parity_claim_not_allowed")
    if packet.get("full_agi_claim") is True:
        errors.append("full_agi_claim_not_allowed")

    status = "PASS" if not missing and not errors else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGAgentSPEXFullHarnessGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "agentspex_full_harness_inspired": True,
        "boundary": BOUNDARY,
    }


def declarative_spec_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """AgentSPEX-inspired: check task evolution has a declarative spec separate from code.

    Spec pattern should have:
    - explicit state (not embedded in code/prompt)
    - typed steps with clear inputs/outputs
    - module reuse (parameterized sub-workflows)
    - control flow (order, conditions, loops, parallel)
    - sandbox isolation or rollback
    """
    required = [
        "spec_format",
        "typed_steps",
        "explicit_state",
    ]
    optional = ["module_reuse", "control_flow", "sandbox_rollback"]
    metrics: list[str] = []
    warnings: list[str] = []
    missing = [field for field in required if not _has(packet, field)]
    spec_format = str(packet.get("spec_format", "")).strip().lower()
    if spec_format and spec_format not in {"yaml", "json", "markdown", "toml", "python_dsl"}:
        warnings.append(f"unknown_spec_format:{spec_format}")
    steps = packet.get("typed_steps") or []
    if isinstance(steps, (list, tuple)):
        if len(steps) < 2:
            warnings.append("less_than_2_typed_steps")
    if not _has(packet, "explicit_state"):
        warnings.append("no_explicit_state")
    if _has(packet, "sandbox_rollback"):
        metrics.append("has_sandbox_rollback")
    if _has(packet, "module_reuse"):
        metrics.append("has_module_reuse")
    status = "PASS" if not missing else "BLOCK"
    if status == "PASS" and warnings:
        status = "WATCH"
    return {
        "schema": "PGGDeclarativeSpecGate/v1",
        "created_at": _now(),
        "status": status,
        "missing": missing,
        "warnings": warnings,
        "metrics": metrics,
        "agentspex_inspired": True,
        "boundary": BOUNDARY,
    }


def evaluate_evolution_pattern_gates(packet: Mapping[str, Any], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    sections = {
        "resource_lineage": resource_lineage_gate(packet.get("resource_lineage", {})),
        "artifact_first": artifact_first_gate(packet.get("artifact_first", {})),
        "gepa_prompt_optimizer": gepa_prompt_optimizer_gate(packet.get("gepa_prompt_optimizer", {})),
        "coral_multi_agent_parallel": coral_multi_agent_parallel_gate(packet.get("coral_multi_agent_parallel", {})),
        "skill_trajectory": skill_trajectory_gate(packet.get("skill_trajectory", {})),
        "skill_body_lapse": skill_body_lapse_separation_gate(packet.get("skill_body_lapse", {})),
        "declarative_spec": declarative_spec_gate(packet.get("declarative_spec", {})),
        "agentspex_full_harness": agentspex_full_harness_gate(packet.get("agentspex_full_harness", {})),
        "population_search": population_search_gate(packet.get("population_search", {})),
        "morphogenetic_acceptance": morphogenetic_acceptance_gate(packet.get("morphogenetic_acceptance", {})),
        "harmrate_growth": harmrate_growth_gate(packet.get("harmrate_growth", {})),
    }
    blocked = [name for name, result in sections.items() if result["status"] not in {"PASS", "WATCH"}]
    summary = {
        "schema": "PGGEvolutionPatternGates/v1",
        "created_at": _now(),
        "status": "PASS" if not blocked else "BLOCK",
        "blocked": blocked,
        "sections": sections,
        "boundary": BOUNDARY,
        "promotion_performed": False,
        "official_source_claim": False,
    }
    if output_dir:
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{int(time.time())}_evolution_pattern_gates.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["output_path"] = str(path)
    return summary


__all__ = [
    "BOUNDARY",
    "resource_lineage_gate",
    "artifact_first_gate",
    "gepa_prompt_optimizer_gate",
    "coral_multi_agent_parallel_gate",
    "skill_trajectory_gate",
    "skill_body_lapse_separation_gate",
    "declarative_spec_gate",
    "agentspex_full_harness_gate",
    "population_search_gate",
    "morphogenetic_acceptance_gate",
    "harmrate_growth_gate",
    "evaluate_evolution_pattern_gates",
]
