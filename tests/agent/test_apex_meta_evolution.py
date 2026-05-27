from agent.apex_meta_evolution import build_meta_evolution_report, summarize_meta_evolution_report
from agent.apex_v3_unified_score import build_apex_v3_unified_score_report


def _complete_meta_status():
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "cron_dryrun": {"unique_keys": 2, "bad_lines": 0, "total_lines": 10, "tasks": {"a": {}}},
        "flow_reward_report": {
            "valid": True,
            "status": "PASS",
            "selected_path_id": "safe",
            "score_delta": 0.1,
            "realized_score": 0.8,
        },
        "switch_cost_report": {"valid": True, "status": "PASS", "net_gain": 0.2},
        "era_report": {"status": "PASS", "selected_path_id": "safe"},
        "co_scientist_report": {"status": "PASS"},
        "quality_gate": {"status": "PASS", "evidence_bundle": {"valid": True}, "missing_blocking_evidence": []},
        "health_report": {"status": "OK"},
        "formula_report": {"status": "PASS", "live_params_used": True},
        "gene_lifecycle_gate": {"status": "PASS", "issues": []},
        "co_scientist_gene_candidate": {"status": "READY", "gene_library_written": False},
        "skill_registry_policy": {"status": "PASS"},
        "promotion_lifecycle_gate": {"status": "PASS"},
        "cross_domain_core_gene_gate": {"status": "PASS"},
        "pending_rollbacks": 0,
        "gep_report": {"status": "WARN"},
    }


def test_meta_evolution_report_passes_with_strategy_flow_and_cost_signals():
    report = build_meta_evolution_report(_complete_meta_status())
    assert report["schema"] == "ApexMetaEvolutionReport/v1"
    assert report["status"] == "PASS"
    assert report["score"] == 100.0
    assert report["cost_sensor"]["valid"] is True
    assert report["llm_validator"]["valid"] is True
    assert report["agi_completion_claim"] is False
    summary = summarize_meta_evolution_report(report)
    assert summary["valid"] is True
    assert summary["status"] == "PASS"


def test_meta_evolution_report_holds_when_core_signals_missing():
    report = build_meta_evolution_report({})
    assert report["status"] == "HOLD"
    assert report["score"] == 0.0
    assert "strategy_ledger" in report["missing"]


def test_unified_score_uses_bound_meta_report_but_keeps_gep_hold():
    status = _complete_meta_status()
    meta = build_meta_evolution_report(status)
    status["meta_evolution_report"] = summarize_meta_evolution_report(meta) | {"signals": meta["signals"]}
    report = build_apex_v3_unified_score_report(status)
    assert report["layers"]["meta_evolution"]["score"] == 100.0
    assert "meta_evolution_incomplete" not in report["hold_reasons"]
    assert "gep_not_fully_pass" in report["hold_reasons"]
    assert report["allows_autonomous_promotion"] is False
    assert report["agi_completion_claim"] is False
