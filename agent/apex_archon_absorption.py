"""PGG Archon guarded absorption gene for APEX/OMEGA learning.

This module turns external AGI/evolution claims into a bounded, testable
absorption candidate.  It is deliberately pure/read-only: no LLM calls, no
filesystem writes, no gene database writes, and no promotion side effects.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Sequence

_SCHEMA = "PGGArchonGuardedAbsorption/v1"
_GENE_SCHEMA = "PGGArchonGuardedAbsorptionGene/v1"

_ACCEPTED_PATTERNS = (
    "teleprompter_high_frequency_standard_llm_calls",
    "era_bounded_path_search",
    "co_scientist_evidence_gated_review",
    "robin_plan_convergence",
    "runtime_interface_design",
    "optimization_read_only_diagnosis",
    "adapter_capability_matrix",
    "engineering_quality_gates",
)

_REJECTED_CLAIMS = (
    "complete_agi_claim",
    "hallucination_elimination_claim",
    "perpetual_self_evolution_claim",
    "zero_vulnerability_claim",
    "unverified_remote_sync_or_pr_claim",
    "unverified_wasm_security_boundary_claim",
)

_REQUIRED_GATES = (
    "schema_contracts",
    "bounded_budget_limits",
    "test_or_readback_evidence",
    "diff_and_remote_verification_for_mutations",
    "multi_model_review_for_agi_or_evolution_claims",
    "fallback_and_rollback_path",
    "human_review_for_high_risk_side_effects",
)

_IMPLEMENTATION_TARGETS = (
    "teleprompter_signature_registry",
    "compiled_prompt_record_with_version_and_eval_set",
    "era_candidate_plan_with_risk_tags",
    "co_scientist_trial_record_with_claim_status",
    "robin_decision_record_with_convergence_limits",
    "runtime_bounded_actor_and_effect_interfaces",
    "optimizer_profile_analyze_suggest_validate_loop",
    "adapter_protocol_version_and_capability_matrix",
    "quality_gate_evidence_bundle",
)


def _safe_text(value: Any, *, limit: int = 240) -> str:
    text = str(value or "").replace("\r", " ").strip()
    lower = text.lower()
    if any(marker in lower for marker in ("api_key", "authorization:", "bearer ", "password", "secret=")):
        return "[REDACTED]"
    return text[:limit]


def _stable_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_guarded_absorption_report(
    *,
    source_materials: Sequence[Mapping[str, Any]] | None = None,
    gpt_review: Mapping[str, Any] | None = None,
    claude_review: Mapping[str, Any] | None = None,
    decision: str = "accept_guarded",
) -> Dict[str, Any]:
    """Build a bounded absorption report for PGG Archon.

    The report records only aggregate model-review facts and fixed gate lists.
    Raw prompts/responses are intentionally excluded so the artifact can be
    committed without leaking credentials or excessive context.
    """
    materials = []
    for item in source_materials or []:
        materials.append({
            "name": _safe_text(item.get("name"), limit=120),
            "kind": _safe_text(item.get("kind"), limit=80),
            "evidence": _safe_text(item.get("evidence"), limit=200),
        })
    model_reviews = []
    for label, review in (("gpt", gpt_review), ("claude", claude_review)):
        if not review:
            model_reviews.append({"channel": label, "status": "missing", "decision": "not_recorded"})
            continue
        model_reviews.append({
            "channel": label,
            "provider": _safe_text(review.get("provider"), limit=80),
            "model": _safe_text(review.get("model"), limit=80),
            "status": _safe_text(review.get("status") or "unknown", limit=40),
            "decision": _safe_text(review.get("decision") or "", limit=120),
            "evidence": _safe_text(review.get("evidence") or "", limit=200),
        })
    ok_reviews = sum(1 for item in model_reviews if item.get("status") == "ok")
    normalized_decision = _safe_text(decision, limit=80)
    report: Dict[str, Any] = {
        "schema": _SCHEMA,
        "status": "PASS" if ok_reviews >= 2 and normalized_decision == "accept_guarded" else "WATCH",
        "decision": normalized_decision,
        "source_materials": materials,
        "model_reviews": model_reviews,
        "accepted_patterns": list(_ACCEPTED_PATTERNS),
        "rejected_claims": list(_REJECTED_CLAIMS),
        "implementation_targets": list(_IMPLEMENTATION_TARGETS),
        "required_gates": list(_REQUIRED_GATES),
        "side_effects": "read_only_report",
        "promotion_required": True,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "credentials_stored": False,
        "applied_to_core_runtime": False,
    }
    report["report_id"] = _stable_hash({
        "schema": report["schema"],
        "decision": report["decision"],
        "accepted_patterns": report["accepted_patterns"],
        "required_gates": report["required_gates"],
    })
    return report


def validate_guarded_absorption_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate structural safety of a guarded absorption report."""
    errors: list[str] = []
    if report.get("schema") != _SCHEMA:
        errors.append("schema")
    if report.get("side_effects") != "read_only_report":
        errors.append("side_effects")
    if report.get("raw_prompts_stored") is not False:
        errors.append("raw_prompts_stored")
    if report.get("raw_responses_stored") is not False:
        errors.append("raw_responses_stored")
    if report.get("credentials_stored") is not False:
        errors.append("credentials_stored")
    if report.get("applied_to_core_runtime") is not False:
        errors.append("applied_to_core_runtime")
    accepted = set(report.get("accepted_patterns") or [])
    rejected = set(report.get("rejected_claims") or [])
    gates = set(report.get("required_gates") or [])
    if not set(_ACCEPTED_PATTERNS).issubset(accepted):
        errors.append("accepted_patterns")
    if not set(_REJECTED_CLAIMS).issubset(rejected):
        errors.append("rejected_claims")
    if not set(_REQUIRED_GATES).issubset(gates):
        errors.append("required_gates")
    return {
        "schema": "PGGArchonGuardedAbsorptionValidation/v1",
        "valid": not errors,
        "errors": errors,
        "side_effects": "read_only_validation",
    }


def build_absorption_gene_candidate(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert a validated report into a non-promoting gene candidate."""
    validation = validate_guarded_absorption_report(report)
    ready = bool(validation["valid"] and report.get("status") == "PASS" and report.get("decision") == "accept_guarded")
    blockers = []
    if not validation["valid"]:
        blockers.append("invalid_report")
    if report.get("status") != "PASS":
        blockers.append("insufficient_model_review")
    if report.get("decision") != "accept_guarded":
        blockers.append("decision_not_guarded_accept")
    return {
        "schema": _GENE_SCHEMA,
        "gene_id": f"archon_guarded_absorption_{report.get('report_id') or 'unknown'}",
        "status": "READY" if ready else "HOLD",
        "eligible": ready,
        "blockers": blockers,
        "evidence_level": "gpt_claude_guarded_architecture_review" if ready else "insufficient",
        "accepted_patterns": list(report.get("accepted_patterns") or []),
        "rejected_claims": list(report.get("rejected_claims") or []),
        "required_gates": list(report.get("required_gates") or []),
        "promotion_required": True,
        "gene_library_written": False,
        "applied_to_memory_or_skill": False,
        "side_effects": "read_only_candidate",
    }


__all__ = [
    "build_absorption_gene_candidate",
    "build_guarded_absorption_report",
    "validate_guarded_absorption_report",
]
