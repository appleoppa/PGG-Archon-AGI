"""PGG Archon cross-domain core gene library gate.

This module turns the user's "avoid a single local scoring gene" requirement
into an executable, read-only control surface.  It does not claim AGI
completion, does not run external science code, and does not mutate gene stores.
Instead it verifies that candidate evolution is anchored across code languages,
scientific domains, skill routing, gene-library lifecycle, and LLM routing.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, Mapping


CORE_GENE_DOMAINS: tuple[dict[str, Any], ...] = (
    {
        "id": "rust_core",
        "label": "Rust core",
        "axis": "code",
        "required": True,
        "evidence": ["ffi_boundary", "cargo_test_or_static_check", "rollback_plan"],
        "anti_game_guard": "must expose a callable boundary or static interface, not only a score constant",
    },
    {
        "id": "python_orchestration",
        "label": "Python orchestration",
        "axis": "code",
        "required": True,
        "evidence": ["pytest_or_import_check", "runtimeos_status_binding", "sanitized_side_effects"],
        "anti_game_guard": "must bind into RuntimeOS/autonomy status, not only create a report file",
    },
    {
        "id": "biology",
        "label": "Biology model constraints",
        "axis": "science",
        "required": True,
        "evidence": ["source_manifest", "external_ground_truth_required", "unit_dimension_or_schema_check"],
        "anti_game_guard": "must cite or encode verifiable constraints; no invented wet-lab capability",
    },
    {
        "id": "chemistry",
        "label": "Chemistry model constraints",
        "axis": "science",
        "required": True,
        "evidence": ["source_manifest", "external_ground_truth_required", "conservation_or_schema_check"],
        "anti_game_guard": "must keep molecule/reaction claims in validation-required mode",
    },
    {
        "id": "physics",
        "label": "Physics model constraints",
        "axis": "science",
        "required": True,
        "evidence": ["source_manifest", "external_ground_truth_required", "dimension_or_invariant_check"],
        "anti_game_guard": "must enforce units/invariants before using scores as truth",
    },
    {
        "id": "mathematics",
        "label": "Mathematics proof constraints",
        "axis": "science",
        "required": True,
        "evidence": ["formal_statement", "test_or_proof_obligation", "counterexample_search"],
        "anti_game_guard": "must distinguish heuristic score from proof/derivation",
    },
    {
        "id": "skill_router",
        "label": "Understand-Anything style skill router",
        "axis": "routing",
        "required": True,
        "evidence": ["task_understanding_schema", "skill_selection_reason", "fallback_when_skill_missing"],
        "anti_game_guard": "must route by task features and missing-context signals, not by one global gene",
    },
    {
        "id": "gene_library",
        "label": "Core gene library lifecycle",
        "axis": "evolution",
        "required": True,
        "evidence": ["candidate_id", "lifecycle_gate", "quality_evidence_bundle", "rollback_or_retirement_rule"],
        "anti_game_guard": "must require lifecycle status and evidence hash before promotion",
    },
    {
        "id": "quantum_llm_router",
        "label": "Quantum LLM route planning",
        "axis": "routing",
        "required": True,
        "evidence": ["route_id_or_fingerprint", "provider_health", "fallback_chain"],
        "anti_game_guard": "must preserve route evidence; role-played model review is invalid",
    },
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def build_cross_domain_core_gene_index() -> Dict[str, Any]:
    """Return a stable, redaction-safe index of required core gene domains."""
    domains = []
    axis_counts: dict[str, int] = {}
    for item in CORE_GENE_DOMAINS:
        axis = str(item["axis"])
        axis_counts[axis] = axis_counts.get(axis, 0) + 1
        domains.append({
            "id": item["id"],
            "label": item["label"],
            "axis": axis,
            "required": bool(item.get("required")),
            "evidence_required": list(item.get("evidence") or []),
            "anti_game_guard_hash": _hash(str(item.get("anti_game_guard") or item["id"])),
        })
    return {
        "schema": "PggArchonCrossDomainCoreGeneIndex/v1",
        "status": "PASS",
        "domain_count": len(domains),
        "axis_counts": axis_counts,
        "domains": domains,
        "minimum_axes_required": ["code", "science", "routing", "evolution"],
        "side_effects": "read_only_report",
        "agi_completion_claim": False,
    }


def _has_route_evidence(status: Mapping[str, Any]) -> bool:
    route = _as_mapping(status.get("quantum_route"))
    if route.get("route_id") or route.get("fingerprint"):
        return True
    cron = _as_mapping(status.get("cron_dryrun"))
    return int(cron.get("unique_keys") or 0) > 0


def _runtime_signal_for_domain(domain_id: str, status: Mapping[str, Any]) -> bool:
    quality = _as_mapping(status.get("quality_gate"))
    gene = _as_mapping(status.get("gene_lifecycle_gate"))
    skill = _as_mapping(status.get("skill_registry_policy"))
    gpo = _as_mapping(status.get("gpo_report"))
    gep = _as_mapping(status.get("gep_report"))
    formula = _as_mapping(status.get("formula_report"))
    sequence = _as_mapping(status.get("sequence_gate"))
    health = _as_mapping(status.get("health_report"))
    co = _as_mapping(status.get("co_scientist_report"))
    era = _as_mapping(status.get("era_report"))

    if domain_id == "rust_core":
        return bool(gpo.get("omega_static_scan")) or _status(health.get("status")) in {"OK", "INFO"}
    if domain_id == "python_orchestration":
        return status.get("schema") == "ApexRuntimeOSAutonomyStatus/v1" and _status(sequence.get("status")) == "PASS"
    if domain_id in {"biology", "chemistry", "physics", "mathematics"}:
        # Scientific domains are activated as constraint surfaces only. They need
        # external ground truth before any factual scientific claim can be made.
        return _status(quality.get("status")) == "PASS" and bool(gpo)
    if domain_id == "skill_router":
        return _status(skill.get("status")) in {"PASS", "WATCH"}
    if domain_id == "gene_library":
        return _status(gene.get("status")) == "PASS" and int(gene.get("promotable_count") or 0) >= 1
    if domain_id == "quantum_llm_router":
        return _has_route_evidence(status) or (_status(co.get("status")) == "PASS" and bool(era.get("selected_path_id")))
    if domain_id == "gep":
        return _status(gep.get("status")) == "PASS"
    if domain_id == "formula":
        return _status(formula.get("status")) == "PASS"
    return False


def build_cross_domain_core_gene_gate(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate cross-domain activation against aggregate RuntimeOS status."""
    index = build_cross_domain_core_gene_index()
    activated = []
    missing = []
    axes_seen: set[str] = set()
    for domain in index["domains"]:
        ok = _runtime_signal_for_domain(str(domain["id"]), status)
        record = {
            "id": domain["id"],
            "axis": domain["axis"],
            "activated": ok,
            "evidence_required_count": len(domain.get("evidence_required") or []),
        }
        activated.append(record)
        if ok:
            axes_seen.add(str(domain["axis"]))
        elif domain.get("required"):
            missing.append(domain["id"])
    required_axes = set(index["minimum_axes_required"])
    missing_axes = sorted(required_axes - axes_seen)
    activated_count = sum(1 for item in activated if item["activated"])
    single_gene_game_risk = len(axes_seen) < len(required_axes) or activated_count < 6
    status_value = "PASS" if not missing and not missing_axes and not single_gene_game_risk else "HOLD"
    return {
        "schema": "PggArchonCrossDomainCoreGeneGate/v1",
        "status": status_value,
        "index": index,
        "activated_count": activated_count,
        "required_count": len(index["domains"]),
        "axis_coverage": sorted(axes_seen),
        "missing_axes": missing_axes,
        "missing_required_domains": missing,
        "single_gene_game_risk": single_gene_game_risk,
        "activated_domains": activated,
        "policy": {
            "scientific_domains_are_constraint_surfaces": True,
            "external_ground_truth_required_before_scientific_claims": True,
            "autonomous_promotion_requires_cross_domain_pass": True,
            "local_score_alone_is_insufficient": True,
        },
        "side_effects": "read_only_report",
        "agi_completion_claim": False,
    }


def build_skill_route_plan(task: str, available_skills: Iterable[str] | None = None) -> Dict[str, Any]:
    """Build an Understand-Anything style deterministic skill route plan.

    The plan is a safe router description: it selects domains from task text and
    reports missing skills instead of pretending that an unavailable external
    Understand-Anything repository is installed.
    """
    text = str(task or "").lower()
    skills = {str(item) for item in (available_skills or [])}
    requested_domains = []
    if any(k in text for k in ("rust", "ffi", "cargo")):
        requested_domains.append("rust_core")
    if any(k in text for k in ("python", "pytest", "runtimeos", "apex", "archon")):
        requested_domains.append("python_orchestration")
    if any(k in text for k in ("biology", "生物")):
        requested_domains.append("biology")
    if any(k in text for k in ("chemistry", "化学")):
        requested_domains.append("chemistry")
    if any(k in text for k in ("physics", "物理")):
        requested_domains.append("physics")
    if any(k in text for k in ("math", "mathematics", "数学", "proof")):
        requested_domains.append("mathematics")
    if any(k in text for k in ("skill", "技能", "understand")):
        requested_domains.append("skill_router")
    if any(k in text for k in ("gene", "基因", "evolution", "进化")):
        requested_domains.append("gene_library")
    if any(k in text for k in ("llm", "量子", "router", "路由")):
        requested_domains.append("quantum_llm_router")
    if not requested_domains:
        requested_domains = ["python_orchestration", "skill_router", "gene_library"]
    requested_domains = list(dict.fromkeys(requested_domains))
    suggested_skills = {
        "rust_core": "rust-core-evolution",
        "python_orchestration": "hermes-agent",
        "biology": "science-biology-validator",
        "chemistry": "science-chemistry-validator",
        "physics": "science-physics-validator",
        "mathematics": "math-proof-validator",
        "skill_router": "understand-anything-skill-router",
        "gene_library": "apex-gene-lifecycle",
        "quantum_llm_router": "quantum-channel-router",
    }
    route = []
    missing_skills = []
    for domain in requested_domains:
        skill = suggested_skills[domain]
        loaded = skill in skills
        route.append({"domain": domain, "suggested_skill": skill, "available": loaded})
        if not loaded:
            missing_skills.append(skill)
    return {
        "schema": "PggArchonSkillRoutePlan/v1",
        "status": "PASS" if not missing_skills else "WATCH",
        "requested_domains": requested_domains,
        "route": route,
        "missing_skills": missing_skills,
        "fallback": "use built-in RuntimeOS gates and explicit external validation before promotion",
        "side_effects": "read_only_report",
    }


__all__ = [
    "build_cross_domain_core_gene_gate",
    "build_cross_domain_core_gene_index",
    "build_skill_route_plan",
]
