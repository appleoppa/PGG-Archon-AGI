from __future__ import annotations

import sqlite3

import pytest

from agent.apex_gene_lifecycle import (
    GeneLifecycleValidationError,
    build_gene_lifecycle_gate_from_runtimeos_status,
    build_gene_lifecycle_gate_report,
    classify_gene_lifecycle_issues,
    classify_gene_lifecycle_issues_from_sqlite,
    load_gene_lifecycle_candidates_from_sqlite,
    normalize_gene_status,
)
from agent.apex_archon_absorption import build_absorption_gene_candidate, build_guarded_absorption_report


def _create_gene_db(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE evolution_genes(
                gene_id TEXT PRIMARY KEY,
                cycle_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                defect_no INTEGER NOT NULL,
                defect_name TEXT NOT NULL,
                gene_name TEXT NOT NULL,
                absorbed_knowledge TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                repair_mechanism TEXT NOT NULL,
                severity_rank INTEGER NOT NULL,
                apex_variables TEXT NOT NULL,
                gate_type TEXT NOT NULL,
                reusable_rule TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_grade TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                boundary TEXT NOT NULL,
                gene_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO evolution_genes VALUES(
                'gene-1','cycle-1','2026-05-26T00:00:00',1,'defect','name','knowledge','[]','repair',1,
                '{}','gate','rule','active','A','pending','boundary','hash-1'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO evolution_genes VALUES(
                'gene-2','cycle-1','2026-05-26T00:01:00',2,'defect','name','knowledge','[]','repair',1,
                '{}','gate','rule','active','A','verified_r2_batch2','boundary','hash-2'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_normalize_gene_status_accepts_only_lifecycle_statuses():
    assert normalize_gene_status("ACTIVE") == "active"
    assert normalize_gene_status("verified") == "verified"
    assert normalize_gene_status("retired") == "retired"
    assert normalize_gene_status("passed") == "verified"
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


def test_load_gene_lifecycle_candidates_from_sqlite_reads_evolution_genes(tmp_path):
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    read = load_gene_lifecycle_candidates_from_sqlite(db, limit=10)
    assert read["schema"] == "ApexRuntimeOSGeneLifecycleSQLiteRead/v1"
    assert read["status"] == "PASS"
    assert read["source_table"] == "evolution_genes"
    assert read["gene_count"] == 2
    assert read["genes"][0]["source_table"] == "evolution_genes"


def test_gene_lifecycle_from_runtimeos_status_reads_configured_sqlite(tmp_path, monkeypatch):
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(db))
    report = build_gene_lifecycle_gate_from_runtimeos_status({"schema": "ApexRuntimeOSAutonomyStatus/v1"})
    assert report["sqlite_read"]["status"] == "PASS"
    assert report["sqlite_read"]["source_table"] == "evolution_genes"
    assert report["gene_count"] == 2
    assert report["counts"]["active"] == 1
    assert report["counts"]["verified"] == 1
    assert report["side_effects"] == "read_only_report"


def test_gene_lifecycle_from_runtimeos_status_blocks_missing_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    report = build_gene_lifecycle_gate_from_runtimeos_status({"schema": "ApexRuntimeOSAutonomyStatus/v1"})
    assert report["status"] == "BLOCK"
    assert report["sqlite_read"]["status"] == "BLOCK"
    assert report["side_effects"] == "read_only_report"


def test_classify_gene_lifecycle_issues_groups_remediations():
    classification = classify_gene_lifecycle_issues([
        {"gene": "g1", "status": "active", "evidence_hash": "h1", "validation_passed": True},
        {"gene": "g2", "status": "verified", "evidence_hash": ""},
        {"gene": "g3", "status": "retired", "evidence_hash": "h3"},
    ])
    assert classification["schema"] == "ApexRuntimeOSGeneLifecycleIssueClassification/v1"
    assert classification["status"] == "WATCH"
    codes = {item["code"] for item in classification["issue_buckets"]}
    assert codes >= {"active_has_validation_but_not_verified", "missing_evidence", "verified_without_validation", "retired_without_reason"}
    remediation_codes = {item["code"] for item in classification["remediation_candidates"]}
    assert remediation_codes >= {"promote_verified_status", "fill_or_hold_missing_evidence", "add_retirement_reason"}
    assert classification["side_effects"] == "read_only_report"


def test_classify_gene_lifecycle_issues_from_sqlite_is_read_only(tmp_path):
    db = tmp_path / "genes.sqlite3"
    _create_gene_db(db)
    classification = classify_gene_lifecycle_issues_from_sqlite(db, limit=10)
    assert classification["sqlite_read"]["status"] == "PASS"
    assert classification["sqlite_read"]["source_table"] == "evolution_genes"
    assert classification["gene_count"] == 2
    assert classification["side_effects"] == "read_only_report"


def test_gene_lifecycle_includes_ready_co_scientist_candidate_when_sqlite_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    status = {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "co_scientist_gene_candidate": {
            "schema": "ApexCoScientistGeneCandidateSummary/v1",
            "status": "READY",
            "eligible": True,
            "candidate_id": "abc123",
            "topic": "co gene",
            "decision": "execute",
            "reviewer_count": 2,
            "evidence_level": "multi_model_debate",
            "promotion_required": True,
            "gene_library_written": False,
            "side_effects": "read_only_candidate",
        },
    }
    report = build_gene_lifecycle_gate_from_runtimeos_status(status)
    assert report["status"] == "PASS"
    assert report["sqlite_read"]["status"] == "BLOCK"
    assert report["co_scientist_gene_candidate"]["present"] is True
    assert report["co_scientist_gene_candidate"]["gene_library_written"] is False
    assert report["gene_count"] == 1
    assert report["promotable_count"] == 1
    assert report["genes"][0]["gene"] == "co_scientist:abc123"


def test_gene_lifecycle_holds_non_ready_co_scientist_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    status = {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "co_scientist_gene_candidate": {
            "schema": "ApexCoScientistGeneCandidateSummary/v1",
            "status": "HOLD",
            "eligible": False,
            "candidate_id": "weak123",
            "topic": "weak gene",
            "decision": "hold",
            "reviewer_count": 1,
            "evidence_level": "insufficient",
            "promotion_required": True,
            "gene_library_written": False,
            "side_effects": "read_only_candidate",
        },
    }
    report = build_gene_lifecycle_gate_from_runtimeos_status(status)
    assert report["status"] == "PASS"
    assert report["co_scientist_gene_candidate"]["present"] is True
    assert report["promotable_count"] == 0
    assert report["genes"][0]["status"] == "active"


def test_gene_lifecycle_includes_ready_archon_absorption_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    absorption_report = build_guarded_absorption_report(
        gpt_review={"status": "ok", "decision": "accept_guarded"},
        claude_review={"status": "ok", "decision": "accept_guarded"},
    )
    candidate = build_absorption_gene_candidate(absorption_report)
    status = {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "archon_absorption_gene_candidate": candidate,
    }
    report = build_gene_lifecycle_gate_from_runtimeos_status(status)
    assert report["status"] == "PASS"
    assert report["sqlite_read"]["status"] == "BLOCK"
    assert report["archon_absorption_gene_candidate"]["present"] is True
    assert report["archon_absorption_gene_candidate"]["eligible"] is True
    assert report["archon_absorption_gene_candidate"]["gene_library_written"] is False
    assert report["gene_count"] == 1
    assert report["promotable_count"] == 1
    assert report["genes"][0]["gene"].startswith("archon_absorption:archon_guarded_absorption_")


def test_gene_lifecycle_holds_non_ready_archon_absorption_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    absorption_report = build_guarded_absorption_report(
        gpt_review={"status": "ok", "decision": "accept_guarded"},
    )
    candidate = build_absorption_gene_candidate(absorption_report)
    status = {
        "schema": "ApexRuntimeOSAutonomyStatus/v1",
        "archon_absorption_gene_candidate": candidate,
    }
    report = build_gene_lifecycle_gate_from_runtimeos_status(status)
    assert report["status"] == "PASS"
    assert report["archon_absorption_gene_candidate"]["present"] is True
    assert report["archon_absorption_gene_candidate"]["eligible"] is False
    assert report["promotable_count"] == 0
    assert report["genes"][0]["status"] == "active"
