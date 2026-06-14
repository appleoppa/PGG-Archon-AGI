from pathlib import Path

from agent.pgg_archon_small_repair_plan import build_pgg_archon_small_repair_plan


def _surface():
    return {
        "schema": "PGGArchonStatusSurface/v1",
        "status": "PASS",
        "score": 100.0,
        "small_bottlenecks": [
            {"code": "Agt/Pan", "source": "case_flow_graph_replay", "next_node": "evidence_gate", "action": "resolve_or_label_next_blocking_case_flow_node", "risk": "low"},
            {"code": "Err/Res", "source": "eval_regression_harness", "failed_count": 1, "action": "verify_p0_alerts_or_convert_to_bounded_repair_cases", "risk": "low"},
            {"code": "Aut/Wrn", "source": "autonomy_status", "mode": "WARN", "action": "review_autopromote_mode_and_clear_warn_state_if_intended", "risk": "low"},
            {"code": "Aut/Guard", "source": "promotion_claim_guard", "hold_reasons": ["human_ack_required"], "action": "clear_promotion_claim_guard_holds_before_autopromote", "risk": "low"},
        ],
    }


def test_pgg_archon_small_repair_plan_converts_evidence_gate_and_eval_bottlenecks(tmp_path):
    plan = build_pgg_archon_small_repair_plan(_surface(), write_report=True, report_dir=tmp_path)

    assert plan["schema"] == "PGGArchonSmallRepairPlan/v1"
    assert plan["repair_count"] == 4
    assert plan["p0_repair_count"] == 3
    assert plan["repairs"][0]["action"] == "create_evidence_gate_resolution_packet"
    assert plan["repairs"][0]["next_node"] == "evidence_gate"
    assert "no_external_delivery" in plan["repairs"][0]["blocked_side_effects"]
    assert plan["repairs"][1]["action"] == "convert_p0_eval_failure_to_expected_red_or_verified_repair_candidate"
    assert "no_gene_write" in plan["repairs"][1]["blocked_side_effects"]
    assert plan["repairs"][2]["action"] == "verify_autonomy_warn_state_and_select_dry_run_or_enforce"
    assert "no_unbounded_autopromotion" in plan["repairs"][2]["blocked_side_effects"]
    assert plan["repairs"][3]["action"] == "resolve_promotion_claim_guard_holds_before_autopromote"
    assert "human_ack_required" in plan["repairs"][3]["hold_reasons"]
    assert "no_agi_completion_claim" in plan["repairs"][3]["blocked_side_effects"]
    assert plan["agi_completion_claim"] is False
    assert Path(plan["report_path"]).exists()


def test_pgg_archon_small_repair_plan_noops_when_no_bottlenecks():
    plan = build_pgg_archon_small_repair_plan({"status": "PASS", "score": 100.0, "small_bottlenecks": []})

    assert plan["repair_count"] == 0
    assert plan["p0_repair_count"] == 0
    assert plan["final_recommendation"] == "no_small_repair_needed"


def test_pgg_archon_small_repair_plan_unknown_source_goes_to_manual_review():
    plan = build_pgg_archon_small_repair_plan({"small_bottlenecks": [{"code": "Net", "source": "unknown_surface"}]})

    assert plan["repair_count"] == 1
    assert plan["repairs"][0]["action"] == "manual_small_bottleneck_review"
    assert plan["repairs"][0]["priority"] == "P2"
    assert plan["repairs"][0]["not_executed"] is True
