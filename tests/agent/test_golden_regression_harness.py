from agent.golden_regression_harness import build_golden_regression_report, clone_artifact, diff_golden_regression, normalize_regression_artifact


def _graph():
    return {
        "schema": "PGGCaseFlowGraphReplay/v1",
        "created_at": "volatile-a",
        "replay_hash": "volatile-hash",
        "nodes": [
            {"node_id": "intake", "status": "PASS"},
            {"node_id": "case_management", "status": "PASS"},
            {"node_id": "evidence_gate", "status": "PASS"},
        ],
        "edges": [
            {"from": "intake", "to": "case_management", "type": "sequential_gate"},
            {"from": "case_management", "to": "evidence_gate", "type": "sequential_gate"},
        ],
    }


def _eval(status="PASS", failed_count=0):
    return {
        "schema": "PGGEvalRegressionHarness/v1",
        "created_at": "volatile-b",
        "eval_hash": "volatile-eval",
        "status": status,
        "case_count": 3,
        "passed_count": 3 - failed_count,
        "failed_count": failed_count,
        "p0_failed_count": 0,
        "alert_count": 0,
        "candidate_count": 0,
    }


def test_normalize_strips_volatile_fields_but_keeps_structure():
    normalized = normalize_regression_artifact(_graph())

    assert "created_at" not in normalized["artifact"]
    assert "replay_hash" not in normalized["artifact"]
    assert normalized["artifact"]["nodes"][0]["node_id"] == "intake"
    assert "artifact_hash" in normalized


def test_golden_diff_passes_happy_case_despite_volatile_noise():
    expected_graph = _graph()
    actual_graph = _graph()
    actual_graph["created_at"] = "volatile-c"
    actual_graph["replay_hash"] = "volatile-other"

    diff = diff_golden_regression(expected_graph=expected_graph, actual_graph=actual_graph, expected_eval=_eval(), actual_eval=_eval())

    assert diff["passed"] is True
    assert diff["graph_structure_diff"]["passed"] is True
    assert diff["node_order_diff"]["passed"] is True
    assert diff["eval_metric_diff"]["passed"] is True
    assert diff["agi_completion_claim"] is False


def test_golden_diff_isolates_deleted_edge_as_graph_structure_diff():
    actual_graph = clone_artifact(_graph())
    actual_graph["edges"] = actual_graph["edges"][:1]

    diff = diff_golden_regression(expected_graph=_graph(), actual_graph=actual_graph, expected_eval=_eval(), actual_eval=_eval())

    assert diff["passed"] is False
    assert diff["graph_structure_diff"]["passed"] is False
    assert diff["node_order_diff"]["passed"] is True
    assert diff["eval_metric_diff"]["passed"] is True
    assert diff["graph_structure_diff"]["missing_edges"] == [["case_management", "evidence_gate", "sequential_gate"]]


def test_golden_diff_isolates_node_order_diff():
    actual_graph = clone_artifact(_graph())
    actual_graph["nodes"] = [actual_graph["nodes"][1], actual_graph["nodes"][0], actual_graph["nodes"][2]]

    diff = diff_golden_regression(expected_graph=_graph(), actual_graph=actual_graph, expected_eval=_eval(), actual_eval=_eval())

    assert diff["passed"] is False
    assert diff["graph_structure_diff"]["passed"] is True
    assert diff["node_order_diff"]["passed"] is False
    assert diff["eval_metric_diff"]["passed"] is True


def test_golden_diff_isolates_eval_metric_diff():
    diff = diff_golden_regression(expected_graph=_graph(), actual_graph=_graph(), expected_eval=_eval(), actual_eval=_eval(status="WARN", failed_count=1))

    assert diff["passed"] is False
    assert diff["graph_structure_diff"]["passed"] is True
    assert diff["node_order_diff"]["passed"] is True
    assert diff["eval_metric_diff"]["passed"] is False
    assert diff["eval_metric_diff"]["changes"]["status"] == {"expected": "PASS", "actual": "WARN"}
    assert diff["eval_metric_diff"]["changes"]["failed_count"] == {"expected": 0, "actual": 1}


def test_golden_report_requires_happy_green_and_negative_red(tmp_path):
    broken_graph = clone_artifact(_graph())
    broken_graph["edges"] = broken_graph["edges"][:1]

    report = build_golden_regression_report(
        [
            {
                "case_id": "happy_case",
                "name": "happy case stays green",
                "expected_graph": _graph(),
                "actual_graph": _graph(),
                "expected_eval": _eval(),
                "actual_eval": _eval(),
                "should_pass": True,
            },
            {
                "case_id": "negative_deleted_edge",
                "name": "negative case stays red",
                "expected_graph": _graph(),
                "actual_graph": broken_graph,
                "expected_eval": _eval(),
                "actual_eval": _eval(),
                "should_pass": False,
            },
        ],
        write_report=True,
        report_dir=tmp_path,
    )

    assert report["status"] == "PASS"
    assert report["case_count"] == 2
    assert report["expectation_met_count"] == 2
    assert report["failed_expectation_count"] == 0
    assert report["cases"][1]["diff"]["graph_structure_diff"]["passed"] is False
    assert report["report_path"].endswith("_golden_regression_report.json")
