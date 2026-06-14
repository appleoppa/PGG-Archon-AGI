from __future__ import annotations

import json

from agent.apex_archon_absorption import (
    build_absorption_gene_candidate,
    build_absorption_quality_evidence_bundle,
    build_absorption_quality_gate_report,
    build_guarded_absorption_report,
    validate_guarded_absorption_report,
)
from runtime.quality.gate_runner import normalize_quality_evidence_bundle


def _review_pair():
    gpt_review = {
        "provider": "gpt55_5yuantoken",
        "model": "gpt-5.5",
        "status": "ok",
        "decision": "accept_guarded",
        "evidence": "accepted teleprompter, ERA/Co_Scientist/Robin, runtime/optimization/adapters/engineering with gates",
    }
    claude_review = {
        "provider": "claude_opus47_5yuantoken",
        "model": "claude-opus-4-7",
        "status": "ok",
        "decision": "accept_guarded",
        "evidence": "accepted guarded engineering absorption and rejected AGI hype claims",
    }
    return gpt_review, claude_review


def test_guarded_absorption_report_accepts_only_bounded_patterns():
    gpt_review, claude_review = _review_pair()
    report = build_guarded_absorption_report(
        source_materials=[
            {"name": "agent进化成agi的过程.md", "kind": "uploaded_reference", "evidence": "read and filtered"},
            {"name": "omega selective absorption", "kind": "repo_doc", "evidence": "readback verified"},
        ],
        gpt_review=gpt_review,
        claude_review=claude_review,
    )

    assert report["schema"] == "PGGArchonGuardedAbsorption/v1"
    assert report["status"] == "PASS"
    assert report["decision"] == "accept_guarded"
    assert "teleprompter_high_frequency_standard_llm_calls" in report["accepted_patterns"]
    assert "co_scientist_evidence_gated_review" in report["accepted_patterns"]
    assert "runtime_interface_design" in report["accepted_patterns"]
    assert "complete_agi_claim" in report["rejected_claims"]
    assert "hallucination_elimination_claim" in report["rejected_claims"]
    assert "perpetual_self_evolution_claim" in report["rejected_claims"]
    assert "multi_model_review_for_agi_or_evolution_claims" in report["required_gates"]
    assert report["raw_prompts_stored"] is False
    assert report["raw_responses_stored"] is False
    assert report["credentials_stored"] is False
    assert report["applied_to_core_runtime"] is False


def test_guarded_absorption_report_redacts_secrets():
    report = build_guarded_absorption_report(
        source_materials=[{"name": "x", "kind": "doc", "evidence": "api_key=secret"}],
        gpt_review={"provider": "gpt", "model": "gpt", "status": "ok", "decision": "accept_guarded"},
        claude_review={"provider": "claude", "model": "claude", "status": "ok", "decision": "accept_guarded"},
    )
    raw = json.dumps(report, ensure_ascii=False)
    assert "api_key=secret" not in raw
    assert "[REDACTED]" in raw


def test_validate_guarded_absorption_report_blocks_claim_injection():
    gpt_review, claude_review = _review_pair()
    report = build_guarded_absorption_report(gpt_review=gpt_review, claude_review=claude_review)
    report["rejected_claims"] = ["complete_agi_claim"]
    validation = validate_guarded_absorption_report(report)
    assert validation["valid"] is False
    assert "rejected_claims" in validation["errors"]


def test_absorption_gene_candidate_is_ready_but_non_promoting():
    gpt_review, claude_review = _review_pair()
    report = build_guarded_absorption_report(gpt_review=gpt_review, claude_review=claude_review)
    candidate = build_absorption_gene_candidate(report)

    assert candidate["schema"] == "PGGArchonGuardedAbsorptionGene/v1"
    assert candidate["status"] == "READY"
    assert candidate["eligible"] is True
    assert candidate["evidence_level"] == "gpt_claude_guarded_architecture_review"
    assert candidate["promotion_required"] is True
    assert candidate["gene_library_written"] is False
    assert candidate["applied_to_memory_or_skill"] is False
    assert candidate["side_effects"] == "read_only_candidate"


def test_absorption_gene_candidate_holds_without_two_ok_reviews():
    report = build_guarded_absorption_report(
        gpt_review={"provider": "gpt", "model": "gpt", "status": "ok", "decision": "accept_guarded"},
    )
    candidate = build_absorption_gene_candidate(report)
    assert candidate["status"] == "HOLD"
    assert candidate["eligible"] is False
    assert "insufficient_model_review" in candidate["blockers"]


def test_absorption_quality_evidence_bundle_is_schema_valid_and_aggregate_only():
    gpt_review, claude_review = _review_pair()
    report = build_guarded_absorption_report(gpt_review=gpt_review, claude_review=claude_review)
    bundle = build_absorption_quality_evidence_bundle(report, test_passed=True)
    normalized = normalize_quality_evidence_bundle(bundle)

    assert bundle["schema"] == "ApexRuntimeOSQualityEvidenceBundle/v1"
    assert normalized["requirements"] is True
    assert normalized["rollback_plan"] is True
    assert normalized["test_report"] is True
    assert normalized["security_review"] is True
    assert normalized["audit_log"] is True
    assert normalized["documentation"] is True


def test_absorption_quality_gate_blocks_without_test_evidence():
    gpt_review, claude_review = _review_pair()
    report = build_guarded_absorption_report(gpt_review=gpt_review, claude_review=claude_review)
    gate = build_absorption_quality_gate_report(report, test_passed=False)

    assert gate["schema"] == "ApexRuntimeOSQualityGateReport/v1"
    assert gate["status"] == "BLOCK"
    assert "test_report" in gate["missing_blocking_evidence"]


def test_absorption_quality_gate_passes_with_test_evidence():
    gpt_review, claude_review = _review_pair()
    report = build_guarded_absorption_report(gpt_review=gpt_review, claude_review=claude_review)
    gate = build_absorption_quality_gate_report(report, test_passed=True)

    assert gate["status"] == "PASS"
    assert gate["evidence_bundle"]["valid"] is True
