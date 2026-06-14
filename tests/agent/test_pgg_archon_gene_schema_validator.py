"""Tests for internal PGG GeneDB schema validator."""

from __future__ import annotations

from agent.pgg_archon_gene_schema_validator import validate_gene_record, validate_gene_records


def _valid_record() -> dict[str, object]:
    return {
        "gene_id": "G1",
        "gene_name": "test gene",
        "absorbed_knowledge": "knowledge",
        "source_refs_json": '[{"source_type":"paper","source_url":"https://example.org"}]',
        "repair_mechanism": "repair",
        "reusable_rule": "rule",
        "status": "candidate",
        "evidence_grade": "B+: test",
        "verification_status": "pending_review",
        "boundary": "bounded candidate",
        "gene_hash": "abc",
    }


def test_valid_candidate_record_passes() -> None:
    ev = validate_gene_record(_valid_record())
    assert ev["valid"] is True
    assert ev["errors"] == []
    assert ev["external_authority"] is False


def test_missing_required_field_fails() -> None:
    record = _valid_record()
    record.pop("source_refs_json")
    ev = validate_gene_record(record)
    assert ev["valid"] is False
    assert "missing:source_refs_json" in ev["errors"]


def test_active_pending_verification_fails() -> None:
    record = _valid_record()
    record["status"] = "active"
    record["verification_status"] = "pending_review_activation_path_intake"
    ev = validate_gene_record(record)
    assert ev["valid"] is False
    assert "active_or_verified_requires_non_pending_verification" in ev["errors"]


def test_external_authority_without_external_ref_fails() -> None:
    record = _valid_record()
    record["external_authority"] = "true"
    record["source_refs_json"] = '[{"source_type":"uploaded_note"}]'
    ev = validate_gene_record(record)
    assert ev["valid"] is False
    assert "external_authority_true_without_external_source_ref" in ev["errors"]


def test_unknown_field_warns_or_fails_when_strict() -> None:
    record = _valid_record()
    record["extra"] = "x"
    ev = validate_gene_record(record)
    assert ev["valid"] is True
    assert "unknown_field:extra" in ev["warnings"]
    strict = validate_gene_record(record, strict_unknown_fields=True)
    assert strict["valid"] is False
    assert "unknown_field:extra" in strict["errors"]


def test_batch_summary_counts(tmp_path) -> None:
    valid = _valid_record()
    invalid = _valid_record()
    invalid["status"] = "bad"
    out = validate_gene_records([valid, invalid], output_dir=tmp_path)
    assert out["total"] == 2
    assert out["valid"] == 1
    assert out["invalid"] == 1
    assert "output_path" in out
