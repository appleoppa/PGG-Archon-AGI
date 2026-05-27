from __future__ import annotations

from agent.apex_gep_external_ingestion import (
    default_external_ingestion_evidence,
    review_external_ingestion_evidence,
)


def test_external_ingestion_gate_passes_with_complete_untrusted_evidence():
    result = review_external_ingestion_evidence(default_external_ingestion_evidence())
    assert result["schema"] == "PggArchonGEPExternalIngestionGate/v1"
    assert result["status"] == "PASS"
    assert result["reason"] == "evidence_complete_untrusted"
    assert result["trusted"] is False
    assert result["executed"] is False
    assert result["network_fetch_performed"] is False
    assert result["gene_written"] is False
    assert result["runtime_input_allowed"] is False
    assert result["agi_completion_claim"] is False
    assert result["allowed_actions"] == ["review_only", "index_only"]


def test_external_ingestion_gate_holds_when_required_fields_missing():
    result = review_external_ingestion_evidence({"source_uri": "local://x"})
    assert result["status"] == "HOLD"
    codes = {item["code"] for item in result["reasons"]}
    assert "missing_sha256" in codes
    assert "missing_evidence" in codes
    assert result["trusted"] is False
    assert result["gene_written"] is False


def test_external_ingestion_gate_rejects_invalid_sha_license_and_policy_unlock():
    evidence = default_external_ingestion_evidence()
    evidence["sha256"] = "bad"
    evidence["license"] = "Unknown"
    evidence["policy"]["runtime_input_allowed"] = True
    evidence["policy"]["gene_write_allowed"] = True
    result = review_external_ingestion_evidence(evidence)
    codes = {item["code"] for item in result["reasons"]}
    assert result["status"] == "HOLD"
    assert "invalid_sha256" in codes
    assert "license_not_allowed" in codes
    assert "policy_forbids_runtime_input_allowed" in codes
    assert "policy_forbids_gene_write_allowed" in codes
    assert result["runtime_input_allowed"] is False
    assert result["gene_written"] is False


def test_external_ingestion_gate_requires_provenance_and_evidence_refs():
    evidence = default_external_ingestion_evidence()
    evidence["provenance"]["chain_of_custody"][0]["evidence_ref"] = "missing-ref"
    result = review_external_ingestion_evidence(evidence)
    codes = {item["code"] for item in result["reasons"]}
    assert result["status"] == "HOLD"
    assert "custody_evidence_ref_missing" in codes
    assert result["executed"] is False


def test_external_ingestion_gate_is_pure_read_only():
    result = review_external_ingestion_evidence(default_external_ingestion_evidence())
    assert result["side_effects"] == "read_only_report"
    assert result["network_fetch_performed"] is False
    assert result["executed"] is False
    assert result["gene_written"] is False
