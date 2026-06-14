from pathlib import Path

from agent.capability_metric_driver import build_capability_metric_driver
from agent.eval_regression_harness import build_eval_regression_harness


def _metrics(status="PASS", score=90.0):
    return {
        "schema": "ApexRealCapabilityMetrics/v1",
        "status": status,
        "overall_score": score,
        "agi_completion_claim": False,
        "metrics": {
            f"m{idx}": {"metric_id": f"m{idx}", "status": "PASS", "score": 90.0, "missing": []}
            for idx in range(1, 10)
        },
    }


def test_eval_harness_passes_clean_metrics_and_driver(tmp_path):
    metrics = _metrics()
    driver = build_capability_metric_driver(metrics)

    report = build_eval_regression_harness(metrics, driver, write_report=True, report_dir=tmp_path)

    assert report["schema"] == "PGGEvalRegressionHarness/v1"
    assert report["status"] == "PASS"
    assert report["failed_count"] == 0
    assert report["known_metric_count"] == 9
    assert report["agi_completion_claim"] is False
    assert Path(report["report_path"]).exists()


def test_eval_harness_blocks_agi_completion_claim():
    metrics = _metrics()
    metrics["agi_completion_claim"] = True

    report = build_eval_regression_harness(metrics, {})

    assert report["status"] == "BLOCK"
    failed = {case["case_id"]: case for case in report["cases"] if not case["passed"]}
    assert failed["metrics_no_agi_completion_claim"]["severity"] == "P0"


def test_eval_harness_warns_when_metric_count_below_floor():
    metrics = _metrics()
    metrics["metrics"] = {"m1": {"metric_id": "m1", "status": "PASS", "score": 90.0}}

    report = build_eval_regression_harness(metrics, {})

    assert report["status"] == "WARN"
    assert report["failed_count"] == 1
    assert report["failure_hints"] == ["collect_more_capability_metric_evidence"]


def test_eval_harness_blocks_p0_alert_budget_but_requires_candidates():
    metrics = {
        "schema": "ApexRealCapabilityMetrics/v1",
        "status": "WATCH",
        "overall_score": 0.0,
        "agi_completion_claim": False,
        "metrics": {"multi_model_evidence": {"metric_id": "multi_model_evidence", "status": "UNKNOWN", "score": None, "missing": []}},
    }
    driver = build_capability_metric_driver(metrics)

    report = build_eval_regression_harness(metrics, driver)

    assert report["status"] == "BLOCK"
    failed = {case["case_id"]: case for case in report["cases"] if not case["passed"]}
    assert "metric_driver_p0_alert_budget" in failed
    assert "metric_driver_candidates_cover_alerts" not in failed
    assert report["candidate_count"] == report["alert_count"]


def test_eval_harness_accepts_custom_regression_cases():
    report = build_eval_regression_harness(
        {},
        {},
        custom_cases=[
            {"case_id": "custom_pass", "name": "custom pass", "expected": "A", "actual": "A"},
            {"case_id": "custom_warn", "name": "custom warn", "expected": 1, "actual": 2, "severity": "P2", "failure_hint": "fix_custom"},
        ],
    )

    assert report["status"] == "WARN"
    assert report["case_count"] == 2
    assert report["failed_count"] == 1
    assert report["failure_hints"] == ["fix_custom"]
