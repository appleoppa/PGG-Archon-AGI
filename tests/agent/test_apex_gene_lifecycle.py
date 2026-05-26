from __future__ import annotations

import pytest

from agent.apex_gene_lifecycle import (
    GeneLifecycleValidationError,
    build_gene_lifecycle_gate_from_runtimeos_status,
    build_gene_lifecycle_gate_report,
    normalize_gene_status,
)


def test_normalize_gene_status_accepts_only_lifecycle_statuses():
    assert normalize_gene_status("ACTIVE") == "active"
    assert normalize_gene_status("verified") == "verified"
    assert normalize_gene_status("retired") == "retired"
    with pytest.raises(GeneLifecycleValidationError):
        normalize_gene_status("external_brain_factory_cycle_verified")


def test_gene_lifecycle_gate_passes_verified_gene_with_evidence():
    report = build_gene_lifecycle_gate_report([
        {"gene": "g1", "status": "verified", "evidence_hash": "abc123", "validation_passed": True},
        {"gene": "g2", "status": "active", "evidence": "report hash only"},
        {"gene": "g3", "status": "retired", "evidence_hash": "def456", "retirement_reason": "replaced"},
    ])
    assert report["schema"] == "ApexRuntimeOSGeneLifecycleGate/v1"
    assert report["status"] == "PASS"
    assert report["counts"] == {"active": 1, "verified": 1, "retired": 1}
    assert report["promotable_count"] == 1
    assert report["side_effects"] == "read_only_report"


def test_gene_lifecycle_gate_blocks_empty_candidates():
    report = build_gene_lifecycle_gate_report([])
    assert report["status"] == "BLOCK"
    assert report["gene_count"] == 0
    assert report["issues"] == [{"code": "no_gene_candidates"}]


def test_gene_lifecycle_gate_warns_missing_evidence_and_invalid_transitions():
    report = build_gene_lifecycle_gate_report([
        {"gene": "g1", "status": "verified", "evidence_hash": ""},
        {"gene": "g2", "status": "retired", "evidence_hash": "abc"},
        {"gene": "g3", "status": "active", "evidence_hash": "abc", "validation_passed": True},
    ])
    codes = {item["code"] for item in report["issues"]}
    assert report["status"] == "WARN"
    assert codes >= {
        "missing_evidence",
        "verified_without_validation",
        "retired_without_reason",
        "active_has_validation_but_not_verified",
    }


def test_gene_lifecycle_gate_rejects_duplicate_and_invalid_status():
    report = build_gene_lifecycle_gate_report([
        {"gene": "g1", "status": "active", "evidence_hash": "abc"},
        {"gene": "g1", "status": "unknown", "evidence_hash": "abc"},
        {"status": "verified", "evidence_hash": "abc", "validation_passed": True},
    ])
    codes = {item["code"] for item in report["issues"]}
    assert "duplicate_gene_id" in codes
    assert "invalid_status" in codes
    assert "missing_gene_id" in codes


def test_gene_lifecycle_from_runtimeos_status_defaults_to_block_without_candidates():
    report = build_gene_lifecycle_gate_from_runtimeos_status({"schema": "ApexRuntimeOSAutonomyStatus/v1"})
    assert report["status"] == "BLOCK"
    assert report["side_effects"] == "read_only_report"
