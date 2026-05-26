from __future__ import annotations

from runtime.quality.gate_runner import evaluate_quality_gate, load_quality_gate


def test_quality_gate_blocks_missing_required_evidence():
    report = evaluate_quality_gate({"requirements": True, "test_report": True})
    assert report["schema"] == "ApexRuntimeOSQualityGateReport/v1"
    assert report["status"] == "BLOCK"
    assert report["blocking_failed"] >= 1
    assert "rollback_plan" in report["missing_blocking_evidence"]
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
    assert report["missing_blocking_evidence"] == []
    assert report["missing_warning_evidence"] == ["documentation"]


def test_quality_gate_passes_all_evidence():
    gate = load_quality_gate()
    evidence = {rule["required_evidence"]: True for rule in gate["rules"]}
    report = evaluate_quality_gate(evidence)
    assert report["status"] == "PASS"
    assert report["blocking_failed"] == 0
    assert report["warning_failed"] == 0
    assert report["evidence_summary"]["documentation"] is True


def test_quality_gate_from_runtimeos_status_is_conservative_read_only():
    from runtime.quality.gate_runner import build_quality_gate_from_runtimeos_status

    report = build_quality_gate_from_runtimeos_status({
        "default_side_effects": "disabled_unless_explicit_enforce",
        "promotion_audit_exists": False,
        "cron_dryrun": {"ledger_exists": False},
    })
    assert report["status"] == "BLOCK"
    assert report["evidence_summary"]["requirements"] is True
    assert report["evidence_summary"]["rollback_plan"] is True
    assert report["evidence_summary"]["test_report"] is False
    assert report["missing_blocking_evidence"] == ["test_report", "audit_log"]
    assert report["boundary"].startswith("CMMI gate is read-only")
