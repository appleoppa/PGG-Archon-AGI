"""Tests for candidate promotion readiness gate."""

from __future__ import annotations

from agent.pgg_archon_candidate_promotion_readiness import (
    evaluate_candidate_promotion_readiness,
    evaluate_candidate_promotion_readiness_batch,
)


def _packet() -> dict[str, object]:
    return {
        "source_evidence": {"status": "VERIFIED_SOURCE"},
        "github_closure": {"status": "VERIFIED_SOURCE"},
        "engineering_factor": {"valid": True, "promotion_allowed": True},
        "gene_schema": {"valid": True, "invalid": 0},
        "evolution_pattern": {"status": "PASS", "promotion_performed": False, "official_source_claim": False},
        "harmrate": {"decision": "ALLOW", "APEX_MOSS_VERIFIED": False, "zero_risk_claim": False},
        "manual_reviewer_approved": True,
        "benchmark_regression_passed": True,
    }


def test_ready_when_all_domains_verified_and_reviewed() -> None:
    out = evaluate_candidate_promotion_readiness(_packet())
    assert out["decision"] == "READY_FOR_REVIEWED_PROMOTION"
    assert out["ready_for_promotion"] is True
    assert out["promotion_performed"] is False


def test_partial_source_holds_pattern_only() -> None:
    packet = _packet()
    packet["github_closure"] = {"status": "REPRO_IMPL"}
    out = evaluate_candidate_promotion_readiness(packet)
    assert out["decision"] == "HOLD_PATTERN_ONLY"
    assert "github_not_official_verified:REPRO_IMPL" in out["holds"]


def test_harmrate_block_blocks() -> None:
    packet = _packet()
    packet["harmrate"] = {"decision": "BLOCK", "APEX_MOSS_VERIFIED": False, "zero_risk_claim": False}
    out = evaluate_candidate_promotion_readiness(packet)
    assert out["decision"] == "BLOCK"
    assert "harmrate_blocks:BLOCK" in out["blocks"]


def test_missing_domains_block() -> None:
    out = evaluate_candidate_promotion_readiness({})
    assert out["decision"] == "BLOCK"
    assert "missing_domain:source_evidence" in out["blocks"]


def test_manual_review_and_benchmark_missing_hold() -> None:
    packet = _packet()
    packet["manual_reviewer_approved"] = False
    packet["benchmark_regression_passed"] = False
    out = evaluate_candidate_promotion_readiness(packet)
    assert out["decision"] == "HOLD_PATTERN_ONLY"
    assert "manual_reviewer_approval_missing" in out["holds"]
    assert "benchmark_regression_missing" in out["holds"]


def test_batch_writes_summary(tmp_path) -> None:
    out = evaluate_candidate_promotion_readiness_batch([_packet(), {}], output_dir=tmp_path)
    assert out["total"] == 2
    assert out["ready_count"] == 1
    assert out["counts"]["BLOCK"] == 1
    assert out["promotion_performed"] is False
    assert "output_path" in out
