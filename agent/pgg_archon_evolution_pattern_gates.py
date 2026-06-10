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
        "skill_trajectory": skill_trajectory_gate(packet.get("skill_trajectory", {})),
        "skill_body_lapse": skill_body_lapse_separation_gate(packet.get("skill_body_lapse", {})),
        "declarative_spec": declarative_spec_gate(packet.get("declarative_spec", {})),
        "population_search": population_search_gate(packet.get("population_search", {})),
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
    "skill_trajectory_gate",
    "skill_body_lapse_separation_gate",
    "declarative_spec_gate",
    "population_search_gate",
    "harmrate_growth_gate",
    "evaluate_evolution_pattern_gates",
]
