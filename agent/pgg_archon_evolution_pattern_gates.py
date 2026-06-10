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


def evaluate_evolution_pattern_gates(packet: Mapping[str, Any], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    sections = {
        "resource_lineage": resource_lineage_gate(packet.get("resource_lineage", {})),
        "artifact_first": artifact_first_gate(packet.get("artifact_first", {})),
        "skill_trajectory": skill_trajectory_gate(packet.get("skill_trajectory", {})),
        "harmrate_growth": harmrate_growth_gate(packet.get("harmrate_growth", {})),
    }
    blocked = [name for name, result in sections.items() if result["status"] != "PASS"]
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
    "harmrate_growth_gate",
    "evaluate_evolution_pattern_gates",
]
