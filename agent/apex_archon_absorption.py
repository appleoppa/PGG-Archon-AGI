"""PGG Archon guarded absorption gene for APEX/OMEGA learning.

This module turns external AGI/evolution claims into a bounded, testable
absorption candidate.  It is deliberately pure/read-only: no LLM calls, no
filesystem writes, no gene database writes, and no promotion side effects.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Sequence

from runtime.quality.evidence_bundle import build_quality_evidence_bundle
from runtime.quality.gate_runner import build_quality_gate_from_runtimeos_status

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


def build_absorption_quality_evidence_bundle(
    report: Mapping[str, Any],
    *,
    test_passed: bool = False,
    audit_present: bool = True,
    documentation_present: bool = True,
) -> Dict[str, Any]:
    """Build a schema-valid quality evidence bundle for absorption promotion.

    Test evidence must be supplied by the caller after running relevant tests;
    this helper never executes commands or upgrades missing tests into a pass.
    """
    validation = validate_guarded_absorption_report(report)
    requirements_present = bool(validation["valid"])
    rollback_present = bool(validation["valid"] and report.get("applied_to_core_runtime") is False)
    security_present = bool(
        validation["valid"]
        and report.get("credentials_stored") is False
        and report.get("raw_prompts_stored") is False
        and report.get("raw_responses_stored") is False
    )
    bundle = build_quality_evidence_bundle(
        test_exit_code=0 if test_passed else 1,
        test_summary="guarded absorption targeted tests passed" if test_passed else "guarded absorption tests not supplied",
        audit_present=audit_present,
        audit_summary="GPT and Claude guarded architecture review recorded" if audit_present else "model review audit missing",
        documentation_present=documentation_present,
        documentation_summary="guarded absorption evidence report and module docs present" if documentation_present else "documentation missing",
        source="pgg-archon-guarded-absorption",
    )
    bundle["evidence"]["requirements"] = {
        "present": requirements_present,
        "summary": "guarded absorption schema and claim boundaries validated" if requirements_present else "guarded absorption report invalid",
        "hash": str(report.get("report_id") or "")[:128],
    }
    bundle["evidence"]["rollback_plan"] = {
        "present": rollback_present,
        "summary": "read-only candidate; rollback is removing the candidate/report files" if rollback_present else "candidate touched core runtime",
    }
    bundle["evidence"]["security_review"] = {
        "present": security_present,
        "summary": "raw prompts, raw responses, credentials, and core runtime application are disabled"
        if security_present
        else "security boundary failed",
    }
    return bundle


def build_absorption_quality_gate_report(report: Mapping[str, Any], *, test_passed: bool = False) -> Dict[str, Any]:
    """Evaluate the standard RuntimeOS quality gate for guarded absorption."""
    bundle = build_absorption_quality_evidence_bundle(report, test_passed=test_passed)
    return build_quality_gate_from_runtimeos_status({
        "default_side_effects": "disabled_unless_explicit_enforce",
        "quality_evidence_bundle": bundle,
    })


__all__ = [
    "build_absorption_gene_candidate",
    "build_absorption_quality_evidence_bundle",
    "build_absorption_quality_gate_report",
    "build_guarded_absorption_report",
    "validate_guarded_absorption_report",
]
