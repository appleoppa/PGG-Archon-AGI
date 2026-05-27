from __future__ import annotations

from agent.apex_gep_resources import (
    build_default_external_resource_manifest,
    build_gep_resource_preflight_report,
    build_resource_index,
    validate_external_resource_manifest,
)


def test_default_gep_external_resource_manifest_is_safe_by_default():
    manifest = build_default_external_resource_manifest()
    validation = validate_external_resource_manifest(manifest)
    assert validation["schema"] == "PggArchonGEPExternalResourceManifestValidation/v1"
    assert validation["status"] == "PASS"
    assert validation["resource_count"] >= 3
    assert validation["all_untrusted"] is True
    assert validation["external_code_execution"] is False
    assert validation["auto_gene_promotion"] is False
    assert validation["agi_completion_claim"] is False


def test_gep_resource_preflight_builds_read_only_index_without_gene_candidate():
    manifest = build_default_external_resource_manifest()
    report = build_gep_resource_preflight_report(manifest)
    assert report["schema"] == "PggArchonGEPResourcePreflight/v1"
    assert report["status"] == "PASS"
    assert report["substatus"] == "RESOURCE_PRECHECK_READY"
    assert report["external_code_execution"] is False
    assert report["credentials_detected"] is False
    assert report["auto_gene_promotion_detected"] is False
    assert report["auto_gene_promotion"] is False
    assert report["write_gene_allowed"] is False
    assert report["agi_completion_claim"] is False
    assert report["resource_index"]["status"] == "READY"
    assert all(item["gene_candidate"] is False for item in report["resource_index"]["entries"])
    assert all(item["trusted"] is False and item["execute_allowed"] is False for item in report["resource_index"]["entries"])


def test_gep_resource_manifest_rejects_execution_credentials_and_trust():
    manifest = build_default_external_resource_manifest()
    bad = dict(manifest)
    resources = [dict(item) for item in manifest["resources"]]
    resources[0]["execute_allowed"] = True
    resources[0]["trusted"] = True
    resources[0]["requires_credentials"] = True
    resources[0]["source_url"] = "ftp://bad.example/resource"
    bad["resources"] = resources
    validation = validate_external_resource_manifest(bad)
    codes = {item["code"] for item in validation["blockers"]}
    assert validation["status"] == "BLOCK"
    assert "external_execution_allowed" in codes
    assert "external_resource_trusted" in codes
    assert "credentials_detected" in codes
    assert "invalid_source_url" in codes


def test_gep_resource_index_is_deterministic():
    manifest = build_default_external_resource_manifest()
    first = build_resource_index(manifest)
    second = build_resource_index(manifest)
    assert first["index_hash"] == second["index_hash"]
    assert first["entry_count"] == second["entry_count"]
