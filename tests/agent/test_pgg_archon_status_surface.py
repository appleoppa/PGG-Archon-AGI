from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def _unlock():
    return {
        "schema": "APEXModuleUnlockRegistry/v1",
        "module_count": 12,
        "unlockable_count": 12,
        "agi_completion_claim": False,
    }


def _graph(status="BLOCK", allows_external_delivery=False):
    return {
        "schema": "PGGCaseFlowGraphReplay/v1",
        "replay_status": status,
        "next_node": "evidence_gate",
        "allows_external_delivery": allows_external_delivery,
        "agi_completion_claim": False,
    }


def _eval(status="BLOCK", failed_count=1):
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


def _autonomy(mode="WARN", autopromote_enabled=True, promotion_count=2, stable_ready_count=1, pending_rollbacks=0):
    return {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "mode": mode,
        "autopromote_enabled": autopromote_enabled,
        "promotion_count": promotion_count,
        "stable_ready_count": stable_ready_count,
        "pending_rollbacks": pending_rollbacks,
        "agi_completion_claim": False,
    }


def test_runtime_status_surface_passes_when_all_surfaces_present_and_safe(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: _autonomy(mode="ENFORCE"))
    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    assert report["schema"] == "PGGArchonStatusSurface/v1"
    assert report["status"] == "PASS"
    assert report["score"] == 100.0
    assert report["missing"] == []
    assert report["summary"]["graph_next_node"] == "evidence_gate"
    assert report["summary"]["autonomy_mode"] == "ENFORCE"
    assert report["summary"]["autopromote_enabled"] is True
    assert report["summary"]["promotion_count"] == 2
    assert report["autonomy_status"]["mode"] == "ENFORCE"
    assert report["small_bottlenecks"][0]["source"] == "case_flow_graph_replay"
    assert report["small_bottlenecks"][0]["next_node"] == "evidence_gate"
    assert report["small_bottlenecks"][1]["source"] == "eval_regression_harness"
    assert report["agi_completion_claim"] is False


def test_runtime_status_surface_flags_warn_autonomy_mode(monkeypatch):
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


def test_runtime_status_surface_blocks_illegal_external_delivery_on_blocked_graph():
    report = build_pgg_archon_status_surface(
        unlock_report=_unlock(),
        graph_replay_report=_graph(status="BLOCK", allows_external_delivery=True),
        eval_regression_report=_eval(),
        golden_regression_report=_golden(),
    )

    assert report["status"] == "WATCH"
    assert "no_external_delivery_from_blocked_graph" in report["missing"]
    assert report["signals"]["no_external_delivery_from_blocked_graph"]["ok"] is False


def test_runtime_status_surface_catches_agi_completion_claim():
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


def test_runtime_status_surface_blocks_when_required_reports_absent():
    report = build_pgg_archon_status_surface(
        unlock_report={},
        graph_replay_report={},
        eval_regression_report={},
        golden_regression_report={},
    )

    assert report["status"] == "BLOCK"
    assert report["score"] < 60
    assert "module_unlock_surface" in report["missing"]
    assert "case_flow_graph_replay_present" in report["missing"]
