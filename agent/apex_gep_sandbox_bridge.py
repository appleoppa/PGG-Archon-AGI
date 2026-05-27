"""PGG Archon GEP static sandbox validator bridge.

The bridge validates a future sandbox-validator evidence document without
starting a sandbox, executing code, importing external modules, opening sockets,
or writing genes. It is an inward verification contract only.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, Mapping

_ALLOWED_SANDBOX_STATUS = {"PASS", "FAIL", "UNKNOWN", "NOT_EXECUTED"}
_FORBIDDEN_KEYS = {
    "code",
    "payload",
    "exec",
    "eval",
    "command",
    "cmd",
    "token",
    "secret",
    "credential",
    "credentials",
    "private_key",
    "api_key",
    "authorization",
}
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _scan_forbidden_keys(obj: Any, *, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            key_text = str(key)
            if key_text.lower() in _FORBIDDEN_KEYS:
                violations.append(f"forbidden_key:{path}.{key_text}")
            violations.extend(_scan_forbidden_keys(value, path=f"{path}.{key_text}"))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden_keys(value, path=f"{path}[{idx}]"))
    return violations


def default_sandbox_validator_bridge_contract() -> Dict[str, Any]:
    return {
        "schema": "PggArchonGEPSandboxValidatorBridgeContract/v1",
        "bridge_mode": "static_contract",
        "side_effects": ["none"],
        "forbidden_modes": ["subprocess", "rpc", "eval", "network", "gene_write"],
        "required_input_fields": [
            "artifact_id",
            "artifact_sha256",
            "sandbox_status",
            "execution_performed",
            "resource_manifest_ref",
        ],
        "allowed_sandbox_status": sorted(_ALLOWED_SANDBOX_STATUS),
        "runtime_unlocked": False,
        "gene_write_allowed": False,
        "agi_completion_claim": False,
    }


def validate_sandbox_validator_bridge_input(document: Mapping[str, Any], contract: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Validate a sandbox bridge evidence input without performing execution."""
    cfg = contract if isinstance(contract, Mapping) else default_sandbox_validator_bridge_contract()
    violations: list[str] = []
    required_raw = cfg.get("required_input_fields")
    required = required_raw if isinstance(required_raw, list) else []
    for field in required:
        if field not in document:
            violations.append(f"missing_field:{field}")

    if document.get("execution_performed") is not False:
        violations.append("execution_performed_must_be_false")
    artifact_sha = str(document.get("artifact_sha256") or "")
    if not _SHA256_RE.fullmatch(artifact_sha):
        violations.append("missing_or_invalid_artifact_sha256")
    status = str(document.get("sandbox_status") or "UNKNOWN").upper()
    if status not in _ALLOWED_SANDBOX_STATUS:
        violations.append("invalid_sandbox_status")
    if cfg.get("bridge_mode") != "static_contract":
        violations.append("bridge_mode_must_be_static_contract")
    if cfg.get("side_effects") != ["none"]:
        violations.append("side_effects_must_be_none")
    violations.extend(_scan_forbidden_keys(document))

    decision = "PASS" if not violations else "BLOCK"
    return {
        "schema": "PggArchonGEPSandboxValidatorBridgeGate/v1",
        "gate": "sandbox_validator_bridge",
        "decision": decision,
        "status": decision,
        "violations": violations,
        "artifact_id": str(document.get("artifact_id") or ""),
        "artifact_sha256_present": bool(_SHA256_RE.fullmatch(artifact_sha)),
        "sandbox_status": status,
        "execution_performed": bool(document.get("execution_performed")),
        "runtime_unlocked": False,
        "gene_write_allowed": False,
        "external_code_execution": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


def build_sandbox_validator_bridge_evidence(document: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Build a redaction-safe bridge evidence package.

    Default document is a synthetic read-only artifact identity, not execution
    output. It is enough to prove the bridge contract is staged while runtime
    execution remains locked.
    """
    default_doc = {
        "artifact_id": "gep-static-validator-contract",
        "artifact_sha256": _stable_hash("gep-static-validator-contract:v1"),
        "sandbox_status": "NOT_EXECUTED",
        "execution_performed": False,
        "resource_manifest_ref": "PggArchonGEPExternalResourceManifest/v1",
    }
    source = document if isinstance(document, Mapping) else default_doc
    gate = validate_sandbox_validator_bridge_input(source)
    checks = {
        "read_only_contract": "PASS" if gate["decision"] == "PASS" else "FAIL",
        "no_runtime_execution": "PASS" if gate["execution_performed"] is False else "FAIL",
        "no_gene_write": "PASS" if gate["gene_write_allowed"] is False else "FAIL",
        "no_secret_fields": "PASS" if not any(str(v).startswith("forbidden_key") for v in gate["violations"]) else "FAIL",
        "schema_valid": "PASS" if gate["artifact_sha256_present"] else "FAIL",
    }
    return {
        "schema": "PggArchonGEPSandboxValidatorBridgeEvidence/v1",
        "ts": time.time(),
        "hold": "sandbox_validator_bridge",
        "decision": gate["decision"],
        "artifact_id": gate["artifact_id"],
        "artifact_sha256_present": gate["artifact_sha256_present"],
        "sandbox_run_id": "not_executed_static_contract",
        "resource_manifest_ref": str(source.get("resource_manifest_ref") or ""),
        "checks": checks,
        "violations": gate["violations"],
        "runtime_unlocked": False,
        "gene_write_allowed": False,
        "external_code_execution": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


__all__ = [
    "build_sandbox_validator_bridge_evidence",
    "default_sandbox_validator_bridge_contract",
    "validate_sandbox_validator_bridge_input",
]
