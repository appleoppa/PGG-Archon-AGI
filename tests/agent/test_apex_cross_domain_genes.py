from __future__ import annotations

from agent.apex_cross_domain_genes import (
    build_cross_domain_core_gene_gate,
    build_cross_domain_core_gene_index,
    build_skill_route_plan,
)
from agent.apex_v3_unified_score import build_apex_v3_unified_score_report


def _status_with_cross_domain(pass_gene: bool = True):
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "health_report": {"status": "OK"},
        "sequence_gate": {"status": "PASS"},
        "quality_gate": {"status": "PASS", "evidence_bundle": {"valid": True}, "missing_blocking_evidence": []},
        "gene_lifecycle_gate": {"status": "PASS", "promotable_count": 1 if pass_gene else 0, "issues": []},
        "skill_registry_policy": {"status": "PASS"},
        "gpo_report": {"status": "PASS", "omega_static_scan": {"scanned_file_count": 12}},
        "cron_dryrun": {"unique_keys": 1, "bad_lines": 0},
        "formula_report": {"status": "PASS", "live_params_used": True},
        "era_report": {"status": "PASS", "selected_path_id": "era-cross-domain"},
        "co_scientist_report": {"status": "PASS"},
        "co_scientist_gene_candidate": {"status": "READY", "gene_library_written": False},
        "flow_reward_report": {"valid": True, "status": "PASS", "score_delta": 0.1},
        "switch_cost_report": {"valid": True, "status": "PASS"},
        "promotion_lifecycle_gate": {"status": "PASS"},
        "gep_report": {"status": "PASS"},
        "pending_rollbacks": 0,
    }


def test_cross_domain_core_gene_index_contains_code_science_routing_evolution_axes():
    index = build_cross_domain_core_gene_index()
    assert index["schema"] == "PggArchonCrossDomainCoreGeneIndex/v1"
    assert index["status"] == "PASS"
    assert index["domain_count"] >= 9
    assert set(index["minimum_axes_required"]) == {"code", "science", "routing", "evolution"}
    assert index["side_effects"] == "read_only_report"
    assert index["agi_completion_claim"] is False


def test_cross_domain_core_gene_gate_passes_only_with_multiple_axes_and_lifecycle():
    status = _status_with_cross_domain(pass_gene=True)
    gate = build_cross_domain_core_gene_gate(status)
    assert gate["schema"] == "PggArchonCrossDomainCoreGeneGate/v1"
    assert gate["status"] == "PASS"
    assert gate["single_gene_game_risk"] is False
    assert gate["activated_count"] >= 6
    assert set(gate["axis_coverage"]) == {"code", "science", "routing", "evolution"}


def test_cross_domain_core_gene_gate_holds_when_gene_library_not_promotable():
    status = _status_with_cross_domain(pass_gene=False)
    gate = build_cross_domain_core_gene_gate(status)
    assert gate["status"] == "HOLD"
    assert "gene_library" in gate["missing_required_domains"]
    assert gate["policy"]["local_score_alone_is_insufficient"] is True


def test_v3_unified_score_blocks_autopromotion_when_cross_domain_gate_holds():
    status = _status_with_cross_domain(pass_gene=False)
    status["cross_domain_core_gene_gate"] = build_cross_domain_core_gene_gate(status)
    report = build_apex_v3_unified_score_report(status)
    assert "cross_domain_core_genes_incomplete" in report["hold_reasons"]
    assert report["allows_autonomous_promotion"] is False


def test_skill_route_plan_maps_understand_anything_style_domains_without_claiming_missing_skills():
    plan = build_skill_route_plan("Rust Python biology chemistry physics mathematics skill gene quantum router", available_skills=["hermes-agent", "quantum-channel-router"])
    assert plan["schema"] == "PggArchonSkillRoutePlan/v1"
    assert plan["status"] == "WATCH"
    assert "rust_core" in plan["requested_domains"]
    assert "biology" in plan["requested_domains"]
    assert "understand-anything-skill-router" in plan["missing_skills"]
    assert plan["side_effects"] == "read_only_report"
