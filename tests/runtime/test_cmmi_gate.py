from __future__ import annotations

from runtime.quality.gate_runner import evaluate_quality_gate, load_quality_gate


def test_quality_gate_blocks_missing_required_evidence():
    report = evaluate_quality_gate({"requirements": True, "test_report": True})
    assert report["schema"] == "ApexRuntimeOSQualityGateReport/v1"
    assert report["status"] == "BLOCK"
    assert report["blocking_failed"] >= 1
    assert report["side_effects"] == "read_only_report"


def test_quality_gate_passes_blocking_and_warns_on_docs_only():
    evidence = {
        "requirements": True,
        "rollback_plan": True,
        "test_report": True,
        "security_review": True,
        "audit_log": True,
        "documentation": False,
    }
    report = evaluate_quality_gate(evidence)
    assert report["blocking_failed"] == 0
    assert report["warning_failed"] == 1
    assert report["status"] == "WARN"


def test_quality_gate_passes_all_evidence():
    gate = load_quality_gate()
    evidence = {rule["required_evidence"]: True for rule in gate["rules"]}
    report = evaluate_quality_gate(evidence)
    assert report["status"] == "PASS"
    assert report["blocking_failed"] == 0
    assert report["warning_failed"] == 0
