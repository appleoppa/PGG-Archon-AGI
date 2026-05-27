from __future__ import annotations

from agent.apex_v3_unified_score import build_apex_v3_unified_score_report


def _status():
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "quality_gate": {"status": "PASS", "evidence_bundle": {"valid": True}, "missing_blocking_evidence": []},
        "health_report": {"status": "OK"},
        "cron_dryrun": {"bad_lines": 0},
        "era_report": {"status": "PASS", "selected_path_id": "safe"},
        "co_scientist_report": {"status": "PASS"},
        "co_scientist_gene_candidate": {"status": "READY", "gene_library_written": False},
        "gene_lifecycle_gate": {"status": "PASS", "issues": [], "gene_count": 1},
        "gep_report": {"status": "WARN"},
        "formula_report": {"status": "PASS", "live_params_used": True},
        "skill_registry_policy": {"status": "PASS"},
        "pending_rollbacks": 0,
        "promotion_lifecycle_gate": {"status": "PASS"},
    }


def test_unified_score_report_is_read_only_and_blocks_autonomous_promotion():
    report = build_apex_v3_unified_score_report(_status())
    assert report["schema"] == "ApexV3UnifiedScoreReport/v1"
    assert report["score"] >= 50
    assert report["allows_next_low_risk_cycle"] is True
    assert report["allows_autonomous_promotion"] is False
    assert report["agi_completion_claim"] is False
    assert report["side_effects"] == "read_only_report"
    assert "gep_not_fully_pass" in report["hold_reasons"]
    assert "meta_evolution_incomplete" in report["hold_reasons"]


def test_unified_score_detects_missing_meta_evolution_controls():
    report = build_apex_v3_unified_score_report(_status())
    meta = report["layers"]["meta_evolution"]
    assert meta["score"] < 60
    assert "strategy_ledger" in meta["missing"]
    assert "shadow_replay" in meta["missing"]
    assert "drift_sensor" in meta["missing"]
    assert "cost_sensor" in meta["missing"]


def test_unified_score_has_p0_recommendations():
    report = build_apex_v3_unified_score_report(_status())
    codes = {item["code"] for item in report["recommendations"]}
    assert "gep_warn_diagnosis" in codes
    assert "evidence_chain_binding" in codes
