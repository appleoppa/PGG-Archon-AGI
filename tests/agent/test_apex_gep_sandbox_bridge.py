from __future__ import annotations

from agent.apex_gep_sandbox_bridge import (
    build_sandbox_validator_bridge_evidence,
    default_sandbox_validator_bridge_contract,
    validate_sandbox_validator_bridge_input,
)

_VALID_INPUT = {
    "artifact_id": "gep-static-validator-contract",
    "artifact_sha256": "a" * 64,
    "sandbox_status": "NOT_EXECUTED",
    "execution_performed": False,
    "resource_manifest_ref": "PggArchonGEPExternalResourceManifest/v1",
}


def test_default_sandbox_validator_contract_is_static_and_no_side_effects():
    contract = default_sandbox_validator_bridge_contract()
    assert contract["schema"] == "PggArchonGEPSandboxValidatorBridgeContract/v1"
    assert contract["bridge_mode"] == "static_contract"
    assert contract["side_effects"] == ["none"]
    assert contract["runtime_unlocked"] is False
    assert contract["gene_write_allowed"] is False
    assert contract["agi_completion_claim"] is False


def test_valid_read_only_sandbox_bridge_input_passes_without_unlocking_runtime():
    result = validate_sandbox_validator_bridge_input(_VALID_INPUT)
    assert result["gate"] == "sandbox_validator_bridge"
    assert result["decision"] == "PASS"
    assert result["violations"] == []
    assert result["execution_performed"] is False
    assert result["runtime_unlocked"] is False
    assert result["gene_write_allowed"] is False
    assert result["external_code_execution"] is False
    assert result["agi_completion_claim"] is False


def test_execution_performed_is_blocked():
    bad = dict(_VALID_INPUT, execution_performed=True)
    result = validate_sandbox_validator_bridge_input(bad)
    assert result["decision"] == "BLOCK"
    assert "execution_performed_must_be_false" in result["violations"]
    assert result["runtime_unlocked"] is False
    assert result["gene_write_allowed"] is False


def test_forbidden_secret_or_command_field_is_blocked():
    bad = dict(_VALID_INPUT, token="redacted", cmd="python evil.py")
    result = validate_sandbox_validator_bridge_input(bad)
    assert result["decision"] == "BLOCK"
    assert any(item.startswith("forbidden_key") for item in result["violations"])
    assert result["runtime_unlocked"] is False
    assert result["gene_write_allowed"] is False


def test_invalid_sandbox_status_is_blocked():
    bad = dict(_VALID_INPUT, sandbox_status="UNLOCK_RUNTIME")
    result = validate_sandbox_validator_bridge_input(bad)
    assert result["decision"] == "BLOCK"
    assert "invalid_sandbox_status" in result["violations"]
    assert result["runtime_unlocked"] is False
    assert result["gene_write_allowed"] is False


def test_missing_artifact_sha256_is_blocked():
    bad = dict(_VALID_INPUT, artifact_sha256="")
    result = validate_sandbox_validator_bridge_input(bad)
    assert result["decision"] == "BLOCK"
    assert "missing_or_invalid_artifact_sha256" in result["violations"]
    assert result["runtime_unlocked"] is False
    assert result["gene_write_allowed"] is False


def test_sandbox_validator_bridge_evidence_is_read_only_package():
    evidence = build_sandbox_validator_bridge_evidence()
    assert evidence["schema"] == "PggArchonGEPSandboxValidatorBridgeEvidence/v1"
    assert evidence["decision"] == "PASS"
    assert evidence["sandbox_run_id"] == "not_executed_static_contract"
    assert evidence["checks"]["read_only_contract"] == "PASS"
    assert evidence["checks"]["no_runtime_execution"] == "PASS"
    assert evidence["checks"]["no_gene_write"] == "PASS"
    assert evidence["runtime_unlocked"] is False
    assert evidence["gene_write_allowed"] is False
    assert evidence["external_code_execution"] is False
    assert evidence["agi_completion_claim"] is False
