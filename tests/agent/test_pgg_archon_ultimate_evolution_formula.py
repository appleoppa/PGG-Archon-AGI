from agent.pgg_archon_ultimate_evolution_formula import (
    build_ars_driver_plan,
    build_report_from_runtime_status,
    build_ultimate_evolution_formula_report,
    compute_evm_full,
    compute_omega_a,
    compute_sigma_delta,
)


def test_ultimate_formula_happy_path_passes():
    report = build_ultimate_evolution_formula_report(
        omega_a=1.2,
        evm_signals={
            "task_success": 90,
            "correctness": 90,
            "closure": 85,
            "reasoning_stability": 80,
            "tool_use": 90,
            "long_context_state": 80,
            "self_repair": 80,
        },
        delta_signals={"hallucination": 0.05, "security": 0.0, "unclosed_debt": 0.05},
    )
    assert report["schema"] == "PGGArchonUltimateEvolutionFormulaReport/v1"
    assert report["formula_name"] == "终极进化公式"
    assert report["status"] == "PASS"
    assert report["score"] >= 75
    assert report["side_effects"] == "read_only_report"


def test_critical_delta_fuse_blocks_even_high_score():
    report = build_ultimate_evolution_formula_report(
        omega_a=2.0,
        evm_signals={name: 100 for name in compute_evm_full({})["components"]},
        delta_signals={"critical": True, "security": 1.0},
    )
    assert report["status"] == "BLOCKED"
    assert report["score"] == 0.0
    assert "p0_critical_delta_fuse_triggered" in report["blockers"]


def test_omega_a_is_bounded_and_can_use_baseline_ratio():
    direct = compute_omega_a(10.0)
    ratio = compute_omega_a(apex_net=120, baseline_net=100)
    assert direct["value"] == 2.0
    assert ratio["value"] == 1.2
    assert ratio["source"] == "net_score_ratio"


def test_sigma_delta_is_normalized_to_100():
    report = compute_sigma_delta({name: 1.0 for name in [
        "hallucination", "security", "unclosed_debt", "cost", "latency",
        "instability", "memory_pollution", "tool_risk", "governance_debt",
    ]})
    assert report["score"] == 100.0
    assert report["raw_score"] == 100.0


def test_ars_plan_is_read_only_and_gpt_primary():
    report = build_ultimate_evolution_formula_report(omega_a=1.0)
    plan = build_ars_driver_plan(report)
    assert plan["schema"] == "PGGArchonUltimateEvolutionARSPlan/v1"
    assert plan["primary_model"] == "gpt55_5yuantoken/gpt-5.5"
    assert plan["side_effects"] == "read_only_plan"
    assert plan["requires_human_authorization_before_core_loop_patch"] is True
    assert any(role["provider"] == "claude_opus47_5yuantoken" for role in plan["model_roles"])


def test_runtime_status_mapping_keeps_boundary():
    runtime_status = {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "quality_gate": {"status": "PASS"},
        "health_report": {"status": "OK"},
        "formula_report": {"status": "PASS"},
        "meta_evolution_report": {"status": "WATCH"},
        "promotion_lifecycle_gate": {"status": "PASS"},
        "gene_lifecycle_gate": {"status": "PASS"},
        "cron_dryrun": {"bad_lines": 0},
    }
    report = build_report_from_runtime_status(runtime_status)
    assert report["schema"] == "PGGArchonUltimateEvolutionFormulaReport/v1"
    assert "不证明AGI完成" in report["capability_boundary"]
