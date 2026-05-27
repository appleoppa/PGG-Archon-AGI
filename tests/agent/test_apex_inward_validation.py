from __future__ import annotations

import pytest

from agent.apex_inward_validator import (
    DualInwardValidator,
    NetworkExecutionDenied,
    OfflineDeterministicValidator,
    TransportInwardValidator,
)
from agent.apex_promotion_claim_guard import PromotionClaimGuard
from agent.apex_v3_unified_score import build_apex_v3_unified_score_report


def _perfect_status():
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "quality_gate": {"status": "PASS", "evidence_bundle": {"valid": True}, "missing_blocking_evidence": []},
        "health_report": {"status": "OK"},
        "cron_dryrun": {"bad_lines": 0, "unique_keys": 1, "total_lines": 1},
        "era_report": {"status": "PASS", "selected_path_id": "safe"},
        "co_scientist_report": {"status": "PASS"},
        "co_scientist_gene_candidate": {"status": "READY", "gene_library_written": False},
        "gene_lifecycle_gate": {"status": "PASS", "issues": [], "gene_count": 1},
        "gep_report": {"status": "PASS", "safety_pipeline": {"actual_execution_allowed": False, "runtime_allowed": False}},
        "formula_report": {"status": "PASS", "live_params_used": True},
        "skill_registry_policy": {"status": "PASS"},
        "pending_rollbacks": 0,
        "promotion_lifecycle_gate": {"status": "PASS"},
        "flow_reward_report": {"valid": True, "status": "PASS", "selected_path_id": "p1", "score_delta": 0.1},
        "switch_cost_report": {"valid": True, "status": "PASS"},
        "meta_evolution_report": {"valid": True, "status": "PASS", "signals": {"strategy_ledger": True, "shadow_replay": True, "drift_sensor": True, "cost_sensor": True}},
        "cross_domain_core_gene_gate": {"status": "PASS"},
    }


def test_dual_inward_validator_passes_safe_snapshot():
    report = build_apex_v3_unified_score_report(_perfect_status())
    result = DualInwardValidator().cross_validate(report)
    assert result.cross_validated is True
    assert result.hold_reasons == ()


def test_dual_inward_validator_detects_agi_claim_violation():
    report = build_apex_v3_unified_score_report(_perfect_status())
    bad = {**report, "agi_completion_claim": True}
    result = DualInwardValidator().cross_validate(bad)
    assert result.cross_validated is False
    assert any("agi_completion_claim_must_remain_false" in reason for reason in result.hold_reasons)


def test_transport_validator_denies_network_by_default():
    validator = TransportInwardValidator("gpt", transport=lambda snapshot: {"status": "PASS", "score": 100})
    with pytest.raises(NetworkExecutionDenied):
        validator.evaluate({"score": 100})


def test_promotion_claim_guard_blocks_without_gep_execution_and_human_ack():
    report = build_apex_v3_unified_score_report(_perfect_status())
    decision = PromotionClaimGuard().evaluate(report, gep_actual_execution_allowed=False, human_ack=False)
    assert decision.allowed is False
    assert "gep_actual_execution_not_allowed" in decision.hold_reasons
    assert "human_ack_required" in decision.hold_reasons


def test_unified_score_exposes_inward_validation_and_claim_guard():
    report = build_apex_v3_unified_score_report(_perfect_status())
    assert report["score"] == 100.0
    assert report["inward_validation"]["cross_validated"] is True
    assert report["promotion_claim_guard"]["allowed"] is False
    assert "gep_actual_execution_not_allowed" in report["promotion_claim_guard"]["hold_reasons"]
    assert report["autonomous_promotion_policy"]["requires_dual_inward_validation"] is True
    assert report["autonomous_promotion_policy"]["requires_human_ack"] is True
    assert report["allows_autonomous_promotion"] is False
    assert report["agi_completion_claim"] is False
