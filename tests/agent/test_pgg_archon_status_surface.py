from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def _unlock():
    return {
        "schema": "APEXModuleUnlockRegistry/v1",
        "module_count": 12,
        "unlockable_count": 12,
        "agi_completion_claim": False,
    }


def _graph(status="PASS", allows_external_delivery=False):
    return {
        "schema": "PGGCaseFlowGraphReplay/v1",
        "replay_status": status,
        "next_node": "evidence_gate",
        "allows_external_delivery": allows_external_delivery,
        "agi_completion_claim": False,
    }


def _eval(status="PASS", failed_count=0):
    return {
        "schema": "PGGEvalRegressionHarness/v1",
        "status": status,
        "failed_count": failed_count,
        "agi_completion_claim": False,
    }


def _golden(status="PASS", failed_expectation_count=0):
    return {
        "schema": "PGGGoldenRegressionReport/v1",
        "status": status,
        "failed_expectation_count": failed_expectation_count,
        "agi_completion_claim": False,
    }


def _autonomy(mode="WARN", autopromote_enabled=True, promotion_count=2, stable_ready_count=1, pending_rollbacks=0, gep_actual_execution_allowed=False):
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "mode": mode,
        "autopromote_enabled": autopromote_enabled,
        "promotion_count": promotion_count,
        "stable_ready_count": stable_ready_count,
        "pending_rollbacks": pending_rollbacks,
        "gep_actual_execution_allowed": gep_actual_execution_allowed,
        "agi_completion_claim": False,
    }


def _passing_report(**overrides):
    """Return a mock report with PASS-like status."""
    data = {
        "schema": "ApexGenericReport/v1",
        "status": "PASS",
        "valid": True,
        "agi_completion_claim": False,
    }
    data.update(overrides)
    return data


def _passing_co_gene(**overrides):
    data = {
        "schema": "ApexCoScientistGeneCandidateSummary/v1",
        "status": "READY",
        "eligible": True,
        "candidate_id": "mock-candidate-001",
        "topic": "mocked",
        "agi_completion_claim": False,
    }
    data.update(overrides)
    return data


def _mock_all_pass(monkeypatch):
    """Set up all monkeypatches so the status surface reaches PASS."""
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: _autonomy(mode="ENFORCE"))
    monkeypatch.setattr("agent.pgg_archon_status_surface.load_latest_era_report", lambda: _passing_report())
    monkeypatch.setattr("agent.pgg_archon_status_surface.load_latest_flow_reward_report", lambda: _passing_report())
    monkeypatch.setattr("agent.pgg_archon_status_surface.load_latest_switch_cost_report", lambda: _passing_report())
    monkeypatch.setattr("agent.pgg_archon_status_surface.load_latest_debate_report", lambda: _passing_report())
    monkeypatch.setattr("agent.pgg_archon_status_surface.load_latest_gene_candidate", _passing_co_gene)
    monkeypatch.setattr("agent.pgg_archon_status_surface.build_gpo_report", lambda: _passing_report(status="PASS"))
    monkeypatch.setattr("agent.pgg_archon_status_surface.load_latest_quality_evidence_bundle", lambda: _passing_report(valid=True))
    monkeypatch.setattr("agent.pgg_archon_status_surface.build_pgg_archon_quality_gate_surface", lambda: _passing_report(schema="PGGArchonQualityGateSurface/v1", status="PASS", blocking_failures=[], warning_failures=[]))
    monkeypatch.setattr(
        "agent.pgg_archon_status_surface.build_pgg_archon_evidence_loop_surface",
        lambda: {"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": False},
    )
    monkeypatch.setattr(
        "agent.pgg_archon_status_surface.build_pgg_archon_apex_agi_absorption_surface",
        lambda: {"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "PASS", "ready_candidate_count": 0, "blocking_failures": [], "agi_completion_claim": False},
    )
    monkeypatch.setattr(
        "agent.pgg_archon_status_surface.build_pgg_archon_p0_surface",
        lambda: {"schema": "PGGArchonP0Surface/v1", "status": "PASS", "aggregate": {"blocking_failures": [], "surfaces_ok": 3, "surfaces_total": 3}, "agi_completion_claim": False},
    )
    monkeypatch.setattr(
        "agent.pgg_archon_status_surface.build_pgg_archon_research_extraction_surface",
        lambda: {"schema": "PGGArchonResearchExtractionSurface/v1", "status": "PASS", "blocking_failures": [], "warning_failures": [], "agi_completion_claim": False},
    )
    monkeypatch.setattr(
        "agent.pgg_archon_status_surface.evaluate_promotion_claim_guard",
        lambda snap: {"schema": "ApexPromotionClaimGuard/v1", "allowed": False, "hold_reasons": ["human_ack_required"], "agi_completion_claim": False},
    )


def test_pgg_archon_status_surface_passes_when_all_surfaces_present_and_safe(monkeypatch):
    _mock_all_pass(monkeypatch)
    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    assert report["schema"] == "PGGArchonStatusSurface/v1"
    assert report["status"] == "PASS", f"Got status={report['status']}, missing={report['missing']}"
    assert report["score"] == 100.0
    assert report["missing"] == []
    assert report["summary"]["graph_next_node"] == "evidence_gate"
    assert report["summary"]["autonomy_mode"] == "ENFORCE"
    assert report["summary"]["autopromote_enabled"] is True
    assert report["summary"]["promotion_count"] == 2
    assert report["summary"]["promotion_guard_allowed"] is False
    assert "human_ack_required" in report["summary"]["promotion_guard_hold_reasons"]
    assert report["autonomy_status"]["mode"] == "ENFORCE"
    assert report["promotion_claim_guard"]["schema"] == "ApexPromotionClaimGuard/v1"
    assert report["small_bottlenecks"][0]["source"] == "promotion_claim_guard"
    assert report["promotion_readiness"]["schema"] == "PGGArchonPromotionReadiness/v1"
    assert report["promotion_readiness"]["status"] == "HUMAN_ACK_REQUIRED"
    assert report["promotion_readiness"]["allows_autonomous_promotion"] is False
    assert report["summary"]["promotion_readiness_status"] == "HUMAN_ACK_REQUIRED"
    assert report["summary"]["promotion_requires_human_ack"] is True
    assert report["summary"]["promotion_human_ack_pending"] is True
    assert report["agi_completion_claim"] is False


def test_pgg_archon_status_surface_flags_warn_autonomy_mode(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: _autonomy(mode="WARN"))

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    assert report["status"] == "WATCH"
    assert report["summary"]["autonomy_mode"] == "WARN"
    assert any(item.get("code") == "Aut/Wrn" for item in report["small_bottlenecks"])
    assert any(item.get("code") == "Aut/Guard" for item in report["small_bottlenecks"])


def test_pgg_archon_status_surface_accepts_explicit_promotion_guard(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: _autonomy(mode="ENFORCE"))

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": []},
    )

    assert report["signals"]["promotion_claim_guard_present"]["ok"] is True
    assert report["summary"]["promotion_guard_allowed"] is True
    assert not any(item.get("code") == "Aut/Guard" for item in report["small_bottlenecks"])


def test_pgg_archon_promotion_readiness_ready_only_when_surface_clean_and_guard_allowed(monkeypatch):
    _mock_all_pass(monkeypatch)

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(status="PASS"),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": [], "agi_completion_claim": False},
        evidence_loop_report={"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": False},
        apex_agi_absorption_report={"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "PASS", "ready_candidate_count": 0, "blocking_failures": [], "agi_completion_claim": False},
        p0_surface_report={"schema": "PGGArchonP0Surface/v1", "status": "PASS", "aggregate": {"blocking_failures": [], "surfaces_ok": 3, "surfaces_total": 3}, "agi_completion_claim": False},
    )

    assert report["status"] == "PASS"
    assert report["missing"] == []
    assert report["small_bottlenecks"] == []
    assert report["promotion_readiness"]["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["promotion_readiness"]["allows_autonomous_promotion"] is False
    assert report["summary"]["promotion_requires_human_ack"] is True
    assert report["summary"]["promotion_human_ack_pending"] is False


def test_pgg_archon_promotion_readiness_keeps_blocked_case_flow_as_gate(monkeypatch):
    _mock_all_pass(monkeypatch)

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(status="BLOCK", allows_external_delivery=False),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": [], "agi_completion_claim": False},
        evidence_loop_report={"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": False},
        apex_agi_absorption_report={"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "PASS", "ready_candidate_count": 0, "blocking_failures": [], "agi_completion_claim": False},
        p0_surface_report={"schema": "PGGArchonP0Surface/v1", "status": "PASS", "aggregate": {"blocking_failures": [], "surfaces_ok": 3, "surfaces_total": 3}, "agi_completion_claim": False},
    )

    assert report["status"] == "PASS"
    assert report["promotion_readiness"]["status"] == "BLOCKED_BY_CASE_FLOW_GATE"
    assert "Agt/Pan" in report["promotion_readiness"]["blocker_codes"]
    assert report["promotion_readiness"]["allows_autonomous_promotion"] is False


def test_pgg_archon_promotion_readiness_requires_guard_allowed_even_without_hold_reasons(monkeypatch):
    _mock_all_pass(monkeypatch)

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(status="PASS"),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": False, "hold_reasons": [], "agi_completion_claim": False},
        evidence_loop_report={"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": False},
        apex_agi_absorption_report={"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "PASS", "ready_candidate_count": 0, "blocking_failures": [], "agi_completion_claim": False},
        p0_surface_report={"schema": "PGGArchonP0Surface/v1", "status": "PASS", "aggregate": {"blocking_failures": [], "surfaces_ok": 3, "surfaces_total": 3}, "agi_completion_claim": False},
    )

    assert report["promotion_readiness"]["status"] == "HUMAN_ACK_REQUIRED"
    assert report["promotion_readiness"]["requires_human_ack"] is True
    assert report["promotion_readiness"]["human_ack_pending"] is True
    assert report["promotion_readiness"]["allows_autonomous_promotion"] is False


def test_pgg_archon_status_surface_blocks_illegal_external_delivery_on_blocked_graph():
    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(status="BLOCK", allows_external_delivery=True),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    assert report["status"] == "WATCH"
    assert "no_external_delivery_from_blocked_graph" in report["missing"]
    assert report["signals"]["no_external_delivery_from_blocked_graph"]["ok"] is False


def test_pgg_archon_status_surface_catches_agi_completion_claim():
    golden = _golden()
    golden["agi_completion_claim"] = True

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=golden,
    )

    assert report["status"] == "WATCH"
    assert "no_agi_completion_claims" in report["missing"]


def test_pgg_archon_status_surface_catches_agi_claim_from_bound_evidence_loop(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: _autonomy(mode="ENFORCE", autopromote_enabled=False))

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(status="PASS"),
        eval_regression_report=_eval(status="PASS", failed_count=0),
        golden_regression_report=_golden(),
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": [], "agi_completion_claim": False},
        evidence_loop_report={"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": True},
    )

    assert report["signals"]["no_agi_completion_claims"]["ok"] is False
    assert "no_agi_completion_claims" in report["missing"]


def test_pgg_archon_status_surface_blocks_when_required_reports_absent(monkeypatch):
    """All required reports absent => BLOCK status."""
    # Monkeypatch standalone loaders to return empty so they don't
    # pick up real files that may exist from prior test runs.
    for mod in (
        "agent.pgg_archon_status_surface.load_latest_era_report",
        "agent.pgg_archon_status_surface.load_latest_flow_reward_report",
        "agent.pgg_archon_status_surface.load_latest_switch_cost_report",
        "agent.pgg_archon_status_surface.load_latest_debate_report",
        "agent.pgg_archon_status_surface.load_latest_gene_candidate",
        "agent.pgg_archon_status_surface.load_latest_quality_evidence_bundle",
    ):
        monkeypatch.setattr(mod, lambda: None)
    monkeypatch.setattr("agent.pgg_archon_status_surface.build_gpo_report", lambda: {})
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: _autonomy(mode="WARN"))
    report = build_pgg_archon_status_surface(
        unlock_report={},
        graph_replay_report={},
        eval_regression_report={},
        golden_regression_report={},
        promotion_guard_report={},
        evidence_loop_report={},
        apex_agi_absorption_report={},
        p0_surface_report={},
        quality_gate_report={},
    )

    assert report["status"] == "BLOCK"
    assert report["score"] < 60
    assert "module_unlock_surface" in report["missing"]
    assert "case_flow_graph_replay_present" in report["missing"]


def test_pgg_archon_status_surface_includes_new_module_fields(monkeypatch):
    """Verify the new module fields appear in the report structure."""
    _mock_all_pass(monkeypatch)
    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    assert "era_report" in report
    assert "flow_reward_report" in report
    assert "switch_cost_report" in report
    assert "co_scientist_debate" in report
    assert "co_scientist_gene_candidate" in report
    assert "gpo_report" in report
    assert "quality_evidence_bundle" in report
    assert report["summary"]["era_status"] == "PASS"
    assert report["summary"]["co_debate_status"] == "PASS"
    assert report["summary"]["co_gene_status"] == "READY"
    assert report["summary"]["gpo_status"] == "PASS"
    assert report["summary"]["quality_evidence_valid"] is True


def test_pgg_archon_status_surface_includes_diagnostic_surface(monkeypatch):
    _mock_all_pass(monkeypatch)

    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    diag = report.get("diagnostic_surface")
    assert isinstance(diag, dict)
    assert diag.get("schema") == "PGGArchonDiagnosticSurface/v1"
    assert diag.get("agi_completion_claim") is False
    # 16 subsystems from existing status_surface inputs
    assert len(diag.get("subsystems", [])) == 16
    assert diag.get("overall_status") in {"PASS", "WATCH", "BLOCK"}
    summary = report["summary"]
    assert "diagnostic_overall_status" in summary
    assert "diagnostic_critical_count" in summary
    assert "diagnostic_degraded_count" in summary
    assert "diagnostic_healthy_count" in summary
    # Counts must equal subsystem totals
    assert (
        summary["diagnostic_critical_count"]
        + summary["diagnostic_degraded_count"]
        + summary["diagnostic_healthy_count"]
    ) == len(diag["subsystems"])
