from pathlib import Path

from agent.pgg_archon_pua_standards import (
    build_pgg_archon_pua_standard_report,
    build_pgg_archon_task_completion_evidence,
)


def test_pua_standard_report_passes_with_no_violations():
    report = build_pgg_archon_pua_standard_report()

    assert report["schema"] == "PGGArchonPUAStandardReport/v1"
    assert report["p0_status"] == "PASS"
    assert report["total_violations"] == 0
    assert len(report["red_lines"]) == 3
    assert len(report["proactivity_standards"]) == 4
    assert report["agi_completion_claim"] is False
    assert report["report_hash"]


def test_pua_standard_report_blocks_red_line_violations():
    report = build_pgg_archon_pua_standard_report(
        red_lines_violated=["close_the_loop", "exhaust_everything"],
    )

    assert report["p0_status"] == "BLOCK"
    assert report["total_violations"] == 2
    assert report["p0_red_line_violations"] == 2
    assert "close_the_loop" in report["violated_red_line_ids"]
    assert "exhaust_everything" in report["violated_red_line_ids"]
    assert "fact_driven" not in report["violated_red_line_ids"]

    red = {r["standard_id"]: r for r in report["red_lines"]}
    assert red["close_the_loop"]["ok"] is False
    assert red["exhaust_everything"]["ok"] is False
    assert red["fact_driven"]["ok"] is True


def test_pua_standard_report_warns_on_proactivity_violations():
    report = build_pgg_archon_pua_standard_report(
        proactivity_violated=["scan_after_fix", "verify_with_output"],
    )

    assert report["p0_status"] == "WARN"
    assert report["total_violations"] == 2
    assert report["p0_red_line_violations"] == 0
    assert "scan_after_fix" in report["violated_proactivity_ids"]

    pro = {p["standard_id"]: p for p in report["proactivity_standards"]}
    assert pro["scan_after_fix"]["ok"] is False
    assert pro["verify_with_output"]["ok"] is False
    assert pro["search_before_ask"]["ok"] is True


def test_pua_standard_report_can_write(tmp_path):
    report = build_pgg_archon_pua_standard_report(
        red_lines_violated=["fact_driven"],
        write_report=True,
        report_dir=tmp_path,
    )

    assert Path(report["report_path"]).exists()
    assert report["p0_status"] == "BLOCK"
    assert report["violated_red_line_ids"] == ["fact_driven"]


def test_task_completion_evidence_rejects_claims_without_output():
    ev = build_pgg_archon_task_completion_evidence("test_task_001", "test task")

    assert ev["task_id"] == "test_task_001"
    assert ev["has_closing_evidence"] is False
    assert ev["evidence_hash"]


def test_task_completion_evidence_accepts_pastable_output():
    ev = build_pgg_archon_task_completion_evidence(
        "test_task_002",
        "real fix",
        build_output="=== Build: 10 passed in 2.3s ===",
        test_output="tests/agent/test_example.py::test_pass PASSED",
    )

    assert ev["has_closing_evidence"] is True
    assert "10 passed" in ev["build_output"]
    assert "PASSED" in ev["test_output"]


def test_task_completion_evidence_can_write(tmp_path):
    ev = build_pgg_archon_task_completion_evidence(
        "PGG-ARCHON-20260528-001",
        "fix evidence gate",
        test_output="15 passed in 8.1s",
        write_report=True,
        report_dir=tmp_path,
    )

    assert ev["has_closing_evidence"] is True
    assert Path(ev["report_path"]).exists()
