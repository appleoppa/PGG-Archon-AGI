from __future__ import annotations

from runtime.quality.gate_runner import (
    evaluate_quality_gate,
    load_evidence_bundle_schema,
    load_quality_gate,
    normalize_quality_evidence_bundle,
)


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
    assert report["evidence_bundle"]["provided"] is False
    assert report["boundary"].startswith("CMMI gate is read-only")


def test_quality_evidence_bundle_schema_loads():
    schema = load_evidence_bundle_schema()
    assert schema["title"] == "APEX RuntimeOS quality evidence bundle"
    assert schema["properties"]["schema"]["const"] == "ApexRuntimeOSQualityEvidenceBundle/v1"


def test_quality_evidence_bundle_normalizes_present_flags():
    bundle = {
        "schema": "ApexRuntimeOSQualityEvidenceBundle/v1",
        "source": "unit-test",
        "evidence": {
            "test_report": {"present": True, "summary": "39 tests passed"},
            "documentation": {"present": False, "summary": "pending"},
        },
    }
    normalized = normalize_quality_evidence_bundle(bundle)
    assert normalized == {"test_report": True, "documentation": False}


def test_quality_gate_from_runtimeos_status_accepts_valid_evidence_bundle():
    from runtime.quality.gate_runner import build_quality_gate_from_runtimeos_status

    bundle = {
        "schema": "ApexRuntimeOSQualityEvidenceBundle/v1",
        "source": "unit-test",
        "evidence": {
            "test_report": {"present": True, "summary": "related tests passed"},
            "audit_log": {"present": True, "summary": "git commit and cron ledger available"},
            "documentation": {"present": True, "summary": "user report updated"},
        },
    }
    report = build_quality_gate_from_runtimeos_status({
        "default_side_effects": "disabled_unless_explicit_enforce",
        "promotion_audit_exists": False,
        "cron_dryrun": {"ledger_exists": False},
        "quality_evidence_bundle": bundle,
    })
    assert report["status"] == "PASS"
    assert report["blocking_failed"] == 0
    assert report["evidence_summary"]["test_report"] is True
    assert report["evidence_summary"]["audit_log"] is True
    assert report["evidence_bundle"]["valid"] is True
    assert "test_report" in report["evidence_bundle"]["keys"]


def test_quality_gate_from_runtimeos_status_reports_invalid_evidence_bundle():
    from runtime.quality.gate_runner import build_quality_gate_from_runtimeos_status

    report = build_quality_gate_from_runtimeos_status({
        "default_side_effects": "disabled_unless_explicit_enforce",
        "quality_evidence_bundle": {"schema": "bad", "evidence": {"test_report": {"present": True}}},
    })
    assert report["status"] == "BLOCK"
    assert report["evidence_bundle"]["provided"] is True
    assert report["evidence_bundle"]["valid"] is False
    assert report["evidence_bundle"]["error"] == "ValidationError"
