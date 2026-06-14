from __future__ import annotations

import json

from agent.pgg_archon_evidence_loop_surface import build_pgg_archon_evidence_loop_surface
from agent.pgg_archon_small_repair_plan import build_pgg_archon_small_repair_plan
from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def _unlock():
    return {"schema": "PGGModuleUnlockRegistry/v1", "module_count": 1, "unlockable_count": 1, "agi_completion_claim": False}


def _graph():
    return {"schema": "PGGCaseFlowGraphReplay/v1", "replay_status": "PASS", "next_node": None, "allows_external_delivery": False, "agi_completion_claim": False}


def _eval():
    return {"schema": "PGGEvalRegressionHarness/v1", "status": "PASS", "failed_count": 0, "agi_completion_claim": False}


def _golden():
    return {"schema": "PGGGoldenRegressionReport/v1", "status": "PASS", "failed_expectation_count": 0, "agi_completion_claim": False}


def _evidence_loop_pass():
    return build_pgg_archon_evidence_loop_surface({
        "events": [
            {"source": "verified_fact", "evidence_hash": "h1", "fact_checked": True},
            {"tool_call": "pytest", "test_result": "pass", "artifact_hash": "h2"},
            {"legal_basis": "民法典", "law_checked": True, "hash": "h3"},
            {"delivered": True, "commit_sha": "abc", "remote_head": "abc", "evidence_hash": "h4"},
        ],
        "failure_sample_library": {"schema": "ApexFailureSampleLibraryStatus/v1", "status": "PASS", "sample_count": 1},
        "failure_samples": [{"error_type": "x", "next_intercept_method": "guard", "evidence_hash": "h5"}],
        "task_retrospective_status": {"schema": "ApexTaskRetrospectiveStatus/v1", "status": "PASS", "retrospective_count": 1},
        "task_retrospectives": [{"what_happened": "x", "why": "y", "next_change": "z", "evidence_hash": "h6"}],
        "autonomy_candidates": [{"candidate_type": "skill_draft", "status": "REVIEW_REQUIRED", "review_required": True, "evidence_hash": "h7"}],
        "multi_model_evidence_ledger": {"schema": "ApexMultiModelEvidenceLedger/v1", "status": "PASS", "provider_count": 1, "entries": [{"provider": "gpt", "model": "m", "status": "RECORDED", "decision": "hold", "evidence_hash": "h8"}]},
    })


def test_pgg_archon_evidence_loop_surface_passes_with_safe_aggregate_evidence():
    report = _evidence_loop_pass()

    assert report["schema"] == "PGGArchonEvidenceLoopSurface/v1"
    assert report["status"] == "PASS"
    assert report["signals"]["event_ledger_observed"]["ok"] is True
    assert report["signals"]["multi_model_evidence_observed"]["ok"] is True
    assert report["real_capability_metrics"]["claims"]["agi_complete"] is False
    assert report["external_calls_made"] is False
    assert report["agi_completion_claim"] is False


def test_pgg_archon_evidence_loop_surface_reads_jsonl_without_raw_content(tmp_path):
    events_path = tmp_path / "case_events.jsonl"
    events_path.write_text(json.dumps({"source": "court", "evidence_hash": "h1", "fact_checked": True}, ensure_ascii=False) + "\n", encoding="utf-8")

    report = build_pgg_archon_evidence_loop_surface({
        "failure_sample_library": {"schema": "ApexFailureSampleLibraryStatus/v1", "status": "UNKNOWN", "sample_count": 0},
        "task_retrospective_status": {"schema": "ApexTaskRetrospectiveStatus/v1", "status": "UNKNOWN", "retrospective_count": 0},
        "multi_model_evidence_ledger": {"schema": "ApexMultiModelEvidenceLedger/v1", "status": "UNKNOWN", "provider_count": 0, "entries": []},
    }, case_events_path=events_path)

    assert report["summary"]["event_count"] == 1
    assert report["signals"]["event_ledger_observed"]["ok"] is True
    assert "failure_learning_observed" in report["missing"]
    assert report["side_effects"] == "read_only_evidence_loop_surface"


def test_status_surface_and_repair_plan_bind_evidence_loop_bottleneck(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"schema": "ApexRuntimeOSAutonomyStatus/v1", "mode": "ENFORCE", "autopromote_enabled": False})
    evidence_loop = {"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "WATCH", "missing": ["task_retrospective_observed"], "agi_completion_claim": False}
    surface = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": []},
        evidence_loop_report=evidence_loop,
    )

    bottleneck = next(item for item in surface["small_bottlenecks"] if item["source"] == "pgg_archon_evidence_loop")
    assert bottleneck["code"] == "Evd/Loop"
    assert surface["summary"]["evidence_loop_status"] == "WATCH"

    plan = build_pgg_archon_small_repair_plan(surface)
    repair = next(item for item in plan["repairs"] if item["source"] == "pgg_archon_evidence_loop")
    assert repair["action"] == "bind_event_failure_retrospective_metric_evidence"
    assert "no_sensitive_content_storage" in repair["blocked_side_effects"]
    assert repair["not_executed"] is True
