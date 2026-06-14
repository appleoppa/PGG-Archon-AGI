from __future__ import annotations

from agent.pgg_archon_quality_gate_surface import (
    SURFACE_VERSION,
    SURFACE_SOURCE_HASH,
    build_pgg_archon_quality_gate_surface,
    default_quality_gates,
)
from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def _passing_context():
    return {
        "improvements": [
            {"id": "i1", "param": "risk", "file": "a.py", "tests_added": 4, "phase": 1},
            {"id": "i2", "param": "gate", "file": "b.py", "tests_added": 3, "phase": 2},
            {"id": "i3", "param": "status", "file": "c.py", "tests_added": 3, "phase": 3},
        ],
        "formula_sensitivity_samples": [0.1, 0.5, 0.9],
        "compilation_status": "PASS",
        "rust_test_status": "PASS",
        "python_test_status": "PASS",
        "new_tests_added": 10,
        "regression_count": 0,
        "metric_improvement_delta": 0.05,
        "full_test_suite_status": "PASS",
        "commit_message": "Bind quality gates into PGG Archon surface",
        "push_status": "PASS",
    }


def _base_status_kwargs():
    return {
        "unlock_report": {"schema": "APEXModuleUnlockRegistry/v1", "module_count": 1, "unlockable_count": 1, "agi_completion_claim": False},
        "graph_replay_report": {"schema": "PGGCaseFlowGraphReplay/v1", "replay_status": "PASS", "next_node": "evidence_gate", "allows_external_delivery": False, "agi_completion_claim": False},
        "eval_regression_report": {"schema": "PGGEvalRegressionHarness/v1", "status": "PASS", "failed_count": 0, "agi_completion_claim": False},
        "golden_regression_report": {"schema": "PGGGoldenRegressionReport/v1", "status": "PASS", "failed_expectation_count": 0, "agi_completion_claim": False},
        "promotion_guard_report": {"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": [], "agi_completion_claim": False},
        "evidence_loop_report": {"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": False},
        "apex_agi_absorption_report": {"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "PASS", "ready_candidate_count": 0, "blocking_failures": [], "agi_completion_claim": False},
        "p0_surface_report": {"schema": "PGGArchonP0Surface/v1", "status": "PASS", "aggregate": {"blocking_failures": [], "surfaces_ok": 3, "surfaces_total": 3}, "agi_completion_claim": False},
    }


def test_quality_gate_surface_passes_full_context():
    report = build_pgg_archon_quality_gate_surface(_passing_context())

    assert report["schema"] == SURFACE_VERSION
    assert report["status"] == "PASS"
    assert report["gate_count"] == 13
    assert report["passed_count"] == 13
    assert report["blocking_failed_count"] == 0
    assert report["warning_failed_count"] == 0
    assert report["agi_completion_claim"] is False
    assert report["side_effects"] == "read_only_report"
    assert report["source_hash"] == SURFACE_SOURCE_HASH


def test_quality_gate_surface_without_context_is_watch_not_block():
    report = build_pgg_archon_quality_gate_surface()

    assert report["schema"] == SURFACE_VERSION
    assert report["status"] == "WATCH"
    assert report["blocking_failed_count"] == 0
    assert "QualityGateContextMissing" in report["warning_failures"]
    assert report["agi_completion_claim"] is False


def test_quality_gate_surface_blocks_incomplete_plan():
    ctx = _passing_context()
    ctx["improvements"] = [{"id": "i1", "file": "a.py"}]
    report = build_pgg_archon_quality_gate_surface(ctx)

    assert report["status"] == "BLOCK"
    assert "PlanCompletenessGate" in report["blocking_failures"]
    assert "PlanMinImprovementsGate" in report["blocking_failures"]


def test_quality_gate_surface_warns_without_optional_evidence():
    ctx = _passing_context()
    ctx.pop("formula_sensitivity_samples")
    ctx["metric_improvement_delta"] = 0
    ctx["push_status"] = "UNKNOWN"
    report = build_pgg_archon_quality_gate_surface(ctx)

    assert report["status"] == "WATCH"
    assert "FormulaSensitivityGate" in report["warning_failures"]
    assert "ImprovementGate" in report["warning_failures"]
    assert "GitHubPushGate" in report["warning_failures"]


def test_quality_gate_definitions_are_phase_ordered_and_bounded():
    gates = default_quality_gates()

    assert len(gates) == 13
    assert [g.phase for g in gates] == sorted(g.phase for g in gates)
    assert {g.severity for g in gates} <= {"blocking", "warning"}


def test_quality_gate_surface_does_not_execute_status_checks():
    """Status fields are evidence labels, not executed commands."""
    ctx = _passing_context()
    ctx["python_test_status"] = "FAIL"
    report = build_pgg_archon_quality_gate_surface(ctx)

    assert report["status"] == "BLOCK"
    assert "PythonTestGate" in report["blocking_failures"]
    assert report["boundary"] == "No compilation, tests, git push, model calls, gene writes, or daemon starts are performed here; only caller-supplied evidence is evaluated."
    assert "No compilation, tests, git push" in report["boundary"]


def test_status_surface_accepts_quality_gate_report(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"mode": "ENFORCE", "autopromote_enabled": False, "promotion_count": 0, "stable_ready_count": 0, "pending_rollbacks": 0, "agi_completion_claim": False})
    quality = build_pgg_archon_quality_gate_surface(_passing_context())
    kwargs = _base_status_kwargs()
    report = build_pgg_archon_status_surface(
        unlock_report=kwargs["unlock_report"],
        graph_replay_report=kwargs["graph_replay_report"],
        eval_regression_report=kwargs["eval_regression_report"],
        golden_regression_report=kwargs["golden_regression_report"],
        promotion_guard_report=kwargs["promotion_guard_report"],
        evidence_loop_report=kwargs["evidence_loop_report"],
        apex_agi_absorption_report=kwargs["apex_agi_absorption_report"],
        p0_surface_report=kwargs["p0_surface_report"],
        quality_gate_report=quality,
    )

    assert report["signals"]["quality_gate_surface_ready"]["ok"] is True
    assert report["summary"]["quality_gate_status"] == "PASS"
    assert not any(item.get("source") == "pgg_archon_quality_gate_surface" for item in report["small_bottlenecks"])


def test_status_surface_marks_quality_gate_block_bottleneck(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"mode": "ENFORCE", "autopromote_enabled": False, "promotion_count": 0, "stable_ready_count": 0, "pending_rollbacks": 0, "agi_completion_claim": False})
    quality = build_pgg_archon_quality_gate_surface({})
    kwargs = _base_status_kwargs()
    report = build_pgg_archon_status_surface(
        unlock_report=kwargs["unlock_report"],
        graph_replay_report=kwargs["graph_replay_report"],
        eval_regression_report=kwargs["eval_regression_report"],
        golden_regression_report=kwargs["golden_regression_report"],
        promotion_guard_report=kwargs["promotion_guard_report"],
        evidence_loop_report=kwargs["evidence_loop_report"],
        apex_agi_absorption_report=kwargs["apex_agi_absorption_report"],
        p0_surface_report=kwargs["p0_surface_report"],
        quality_gate_report=quality,
    )

    assert report["signals"]["quality_gate_surface_ready"]["ok"] is False
    assert any(item.get("code") == "QG/Block" for item in report["small_bottlenecks"])


def test_status_surface_rejects_malformed_quality_gate_report(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"mode": "ENFORCE", "autopromote_enabled": False, "promotion_count": 0, "stable_ready_count": 0, "pending_rollbacks": 0, "agi_completion_claim": False})
    malformed_quality = {"schema": "Wrong/v1", "status": "PASS", "agi_completion_claim": False}
    kwargs = _base_status_kwargs()
    report = build_pgg_archon_status_surface(
        unlock_report=kwargs["unlock_report"],
        graph_replay_report=kwargs["graph_replay_report"],
        eval_regression_report=kwargs["eval_regression_report"],
        golden_regression_report=kwargs["golden_regression_report"],
        promotion_guard_report=kwargs["promotion_guard_report"],
        evidence_loop_report=kwargs["evidence_loop_report"],
        apex_agi_absorption_report=kwargs["apex_agi_absorption_report"],
        p0_surface_report=kwargs["p0_surface_report"],
        quality_gate_report=malformed_quality,
    )

    assert report["signals"]["quality_gate_surface_ready"]["ok"] is False
    assert report["summary"]["quality_gate_schema_ok"] is False
    assert any(item.get("code") == "QG/Schema" for item in report["small_bottlenecks"])
