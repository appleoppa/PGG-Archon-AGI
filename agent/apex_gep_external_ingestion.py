"""PGG Archon GEP external ingestion evidence gate.

This gate reviews already-present provenance/license/checksum/evidence metadata.
It does not fetch network resources, execute artifacts, trust external sources,
or write genes. PASS means the ingestion evidence package is structurally ready
for human review; it does not mean the resource is trusted runtime input.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Mapping

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "CC0-1.0", "CC-BY-4.0", "Internal-Only"}
_REQUIRED_FIELDS = ("source_uri", "sha256", "fetched_at", "fetcher", "license", "provenance", "evidence")


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def default_external_ingestion_evidence() -> Dict[str, Any]:
    source_uri = "local://external/super-evolution-core/evolver-main/src/gep"
    license_evidence = _stable_hash("internal-license-evidence:v1")
    provenance_evidence = _stable_hash("local-archive-provenance:v1")
    return {
        "schema": "PggArchonGEPExternalIngestionEvidence/v1",
        "source_uri": source_uri,
        "sha256": _stable_hash(source_uri),
        "fetched_at": "not_fetched_local_reference_only",
        "fetcher": "read_only_manifest_index",
        "license": "Internal-Only",
        "intended_use": "index_only",
        "provenance": {
            "origin_name": "external-super-evolution-core-archive",
            "retrieved_by": "local_manifest",
            "chain_of_custody": [
                {"step": "indexed_as_reference_only", "evidence_ref": "provenance-note"},
            ],
        },
        "evidence": [
            {"evidence_id": "license-note", "kind": "license", "checksum_sha256": license_evidence},
            {"evidence_id": "provenance-note", "kind": "provenance", "checksum_sha256": provenance_evidence},
        ],
        "policy": {
            "allowed_actions": ["review_only", "index_only"],
            "runtime_input_allowed": False,
            "network_fetch_allowed": False,
            "external_code_execution": False,
            "trusted": False,
            "gene_write_allowed": False,
            "agi_completion_claim": False,
        },
    }


def review_external_ingestion_evidence(evidence: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = evidence if isinstance(evidence, Mapping) else default_external_ingestion_evidence()
    reasons: list[Dict[str, str]] = []
    refs: list[str] = []
    for field in _REQUIRED_FIELDS:
        if field in data:
            refs.append(field)
        else:
            reasons.append({"gate": "schema", "code": f"missing_{field}", "message": f"missing required field: {field}"})

    sha = str(data.get("sha256") or "")
    if not _SHA256_RE.fullmatch(sha):
        reasons.append({"gate": "checksum", "code": "invalid_sha256", "message": "sha256 must be 64 hex chars"})
    license_id = str(data.get("license") or "")
    intended_use = str(data.get("intended_use") or "index_only")
    if license_id not in _ALLOWED_LICENSES:
        reasons.append({"gate": "license", "code": "license_not_allowed", "message": "license is not in allowlist"})
    if license_id == "Internal-Only" and intended_use not in {"index_only", "review_only"}:
        reasons.append({"gate": "license", "code": "internal_only_use_violation", "message": "Internal-Only permits index/review only"})

    provenance_raw = data.get("provenance")
    provenance: Mapping[str, Any] = provenance_raw if isinstance(provenance_raw, Mapping) else {}
    custody_raw = provenance.get("chain_of_custody")
    custody = custody_raw if isinstance(custody_raw, list) else []
    if not provenance.get("origin_name"):
        reasons.append({"gate": "provenance", "code": "missing_origin_name", "message": "origin name required"})
    if not provenance.get("retrieved_by"):
        reasons.append({"gate": "provenance", "code": "missing_retrieved_by", "message": "retrieved_by required"})
    if not custody:
        reasons.append({"gate": "provenance", "code": "missing_chain_of_custody", "message": "chain of custody required"})

    evidence_raw = data.get("evidence")
    evidence_items = evidence_raw if isinstance(evidence_raw, list) else []
    evidence_ids = {str(item.get("evidence_id")) for item in evidence_items if isinstance(item, Mapping) and item.get("evidence_id")}
    if not evidence_items:
        reasons.append({"gate": "evidence", "code": "missing_evidence_items", "message": "at least one evidence item required"})
    for item in evidence_items:
        if not isinstance(item, Mapping):
            reasons.append({"gate": "evidence", "code": "malformed_evidence_item", "message": "evidence item must be mapping"})
            continue
        if not item.get("evidence_id") or not item.get("kind"):
            reasons.append({"gate": "evidence", "code": "missing_evidence_identity", "message": "evidence_id and kind required"})
        checksum = str(item.get("checksum_sha256") or "")
        if not _SHA256_RE.fullmatch(checksum):
            reasons.append({"gate": "evidence", "code": "invalid_evidence_checksum", "message": "evidence checksum must be sha256"})
    for step in custody:
        if not isinstance(step, Mapping):
            continue
        ref = str(step.get("evidence_ref") or "")
        if ref and ref not in evidence_ids:
            reasons.append({"gate": "provenance", "code": "custody_evidence_ref_missing", "message": "custody references missing evidence"})

    policy_raw = data.get("policy")
    policy: Mapping[str, Any] = policy_raw if isinstance(policy_raw, Mapping) else {}
    forbidden_policy = {
        "runtime_input_allowed": bool(policy.get("runtime_input_allowed")),
        "network_fetch_allowed": bool(policy.get("network_fetch_allowed")),
        "external_code_execution": bool(policy.get("external_code_execution")),
        "trusted": bool(policy.get("trusted")),
        "gene_write_allowed": bool(policy.get("gene_write_allowed")),
        "agi_completion_claim": bool(policy.get("agi_completion_claim")),
    }
    for key, value in forbidden_policy.items():
        if value:
            reasons.append({"gate": "policy", "code": f"policy_forbids_{key}", "message": f"{key} must remain false"})

    status = "PASS" if not reasons else "HOLD"
    return {
        "schema": "PggArchonGEPExternalIngestionGate/v1",
        "status": status,
        "decision": status,
        "reason": "evidence_complete_untrusted" if status == "PASS" else "evidence_incomplete_or_policy_blocked",
        "reasons": reasons,
        "trusted": False,
        "executed": False,
        "network_fetch_performed": False,
        "gene_written": False,
        "runtime_input_allowed": False,
        "allowed_actions": ["review_only", "index_only"] if status == "PASS" else ["review_only"],
        "evidence_refs": refs,
        "side_effects": "read_only_report",
        "agi_completion_claim": False,
    }


__all__ = ["default_external_ingestion_evidence", "review_external_ingestion_evidence"]
