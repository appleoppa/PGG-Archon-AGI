"""Tests for GeneDB promotion precheck."""

from __future__ import annotations

from agent.pgg_archon_genedb_promotion_precheck import (
    build_readiness_packets_from_gene_records,
    evaluate_precheck_on_records,
)


def _candidate(gene_id: str, status: str, verification: str) -> dict[str, object]:
    return {
        "gene_id": gene_id,
        "gene_name": "test",
        "boundary": "bounded",
        "source_refs_json": "[{}]",
        "gene_hash": "abc",
        "status": status,
        "verification_status": verification,
        "apex_variables": "12534",
        "severity_rank": 3,
    }


def test_ready_candidate_produces_hold_or_ready(tmp_path) -> None:
    # A candidate with active+verified statuses plus all fields.
    records = [
        _candidate("G1", "active", "verified"),
        _candidate("G2", "candidate", "pending_review"),
    ]
    packets = build_readiness_packets_from_gene_records(records)
    assert len(packets) == 2
    assert packets[0]["source_evidence"]["status"] == "VERIFIED_SOURCE"
    assert packets[1]["source_evidence"]["status"] == "HYPOTHESIS_ONLY"


def test_precheck_runs_without_promotion(tmp_path) -> None:
    records = [_candidate("G1", "active", "verified")]
    out = evaluate_precheck_on_records(records, output_dir=tmp_path)
    assert out["total"] == 1
    assert out["promotion_performed"] is False
