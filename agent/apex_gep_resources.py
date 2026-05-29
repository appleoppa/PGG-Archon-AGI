"""PGG Archon GEP external resource preflight.

This module turns external/archived GEP blockers into a read-only resource
inventory and preflight report. It never executes external code, never fetches
network resources, and never writes genes.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

_ALLOWED_TYPES = {"documentation", "dataset", "spec", "paper", "metadata"}
_ALLOWED_USES = {"index_only", "read_only_reference", "manual_review_only"}
_REQUIRED_FIELDS = (
    "id",
    "type",
    "source_url",
    "license",
    "allowed_use",
    "requires_credentials",
    "trusted",
    "mirror_allowed",
    "execute_allowed",
    "expected_sha256",
)
_SECRET_RE = re.compile(r"(api[_-]?key|authorization|bearer\s+|password|secret|token\s*=)", re.I)
_AUTO_PROMOTION_RE = re.compile(r"(auto[_-]?gene[_-]?promotion|auto[_-]?promotion|write[_-]?gene)", re.I)


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _status_from_issues(blockers: Sequence[Mapping[str, Any]]) -> str:
    return "PASS" if not blockers else "BLOCK"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_default_external_resource_manifest() -> Dict[str, Any]:
    """Return the minimal safe resource manifest for current GEP blockers."""
    return {
        "schema": "PggArchonGEPExternalResourceManifest/v1",
        "version": "0.1",
        "resources": [
            {
                "id": "archived-gep-memorygraph",
                "type": "metadata",
                "source_url": "local://external/super-evolution-core/evolver-main/src/gep/memoryGraph.js",
                "license": "unknown",
                "allowed_use": "manual_review_only",
                "requires_credentials": False,
                "trusted": False,
                "mirror_allowed": False,
                "execute_allowed": False,
                "expected_sha256": None,
                "blocker": "obfuscated_archive",
                "origin_note": "Archived obfuscated GEP component; index metadata only until manual review.",
            },
            {
                "id": "archived-gep-narrativememory",
                "type": "metadata",
                "source_url": "local://external/super-evolution-core/evolver-main/src/gep/narrativeMemory.js",
                "license": "unknown",
                "allowed_use": "manual_review_only",
                "requires_credentials": False,
                "trusted": False,
                "mirror_allowed": False,
                "execute_allowed": False,
                "expected_sha256": None,
                "blocker": "obfuscated_archive",
                "origin_note": "Archived obfuscated GEP component; index metadata only until manual review.",
            },
            {
                "id": "gep-validator-static-contract",
                "type": "spec",
                "source_url": "local://runtime/gep/validator_contract.schema.json",
                "license": "internal",
                "allowed_use": "index_only",
                "requires_credentials": False,
                "trusted": False,
                "mirror_allowed": False,
                "execute_allowed": False,
                "expected_sha256": None,
                "blocker": "sandbox_validator_bridge",
                "origin_note": "Static contract only; no subprocess, RPC, eval, or sandbox launch.",
            },
        ],
        "policy": {
            "external_code_execution": False,
            "auto_gene_promotion": False,
            "write_gene_allowed": False,
            "agi_completion_claim": False,
            "default_trusted": False,
        },
    }


def validate_external_resource_manifest(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    resources = _as_list(manifest.get("resources"))
    blockers: list[Dict[str, Any]] = []
    warnings: list[Dict[str, Any]] = []
    seen: set[str] = set()
    policy_raw = manifest.get("policy")
    policy: Mapping[str, Any] = policy_raw if isinstance(policy_raw, Mapping) else {}

    if manifest.get("schema") != "PggArchonGEPExternalResourceManifest/v1":
        blockers.append({"code": "invalid_schema"})
    if not isinstance(resources, list):
        blockers.append({"code": "resources_not_list"})

    for idx, raw in enumerate(resources):
        if not isinstance(raw, Mapping):
            blockers.append({"code": "resource_not_mapping", "index": idx})
            continue
        rid = str(raw.get("id") or "").strip()
        missing = [field for field in _REQUIRED_FIELDS if field not in raw]
        if missing:
            blockers.append({"code": "missing_required_fields", "index": idx, "id": rid or None, "fields": missing})
        if not rid:
            blockers.append({"code": "missing_id", "index": idx})
        elif rid in seen:
            blockers.append({"code": "duplicate_id", "id": rid})
        seen.add(rid)
        rtype = raw.get("type")
        if rtype not in _ALLOWED_TYPES:
            blockers.append({"code": "disallowed_type", "id": rid, "type": rtype})
        allowed_use = raw.get("allowed_use")
        if allowed_use not in _ALLOWED_USES:
            blockers.append({"code": "disallowed_use", "id": rid, "allowed_use": allowed_use})
        source_url = str(raw.get("source_url") or "")
        if not (source_url.startswith("http://") or source_url.startswith("https://") or source_url.startswith("local://")):
            blockers.append({"code": "invalid_source_url", "id": rid})
        joined = json.dumps(raw, ensure_ascii=False)
        if _SECRET_RE.search(joined) or bool(raw.get("requires_credentials")):
            blockers.append({"code": "credentials_detected", "id": rid})
        if _AUTO_PROMOTION_RE.search(joined) and raw.get("allowed_use") == "auto_gene_promotion":
            blockers.append({"code": "auto_gene_promotion_detected", "id": rid})
        if bool(raw.get("execute_allowed")):
            blockers.append({"code": "external_execution_allowed", "id": rid})
        if bool(raw.get("trusted")):
            blockers.append({"code": "external_resource_trusted", "id": rid})
        expected = raw.get("expected_sha256")
        if expected is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(expected)):
            blockers.append({"code": "invalid_expected_sha256", "id": rid})
        if raw.get("license") == "unknown":
            warnings.append({"code": "license_unknown", "id": rid})

    if bool(policy.get("external_code_execution")):
        blockers.append({"code": "policy_allows_external_execution"})
    if bool(policy.get("auto_gene_promotion")) or bool(policy.get("write_gene_allowed")):
        blockers.append({"code": "policy_allows_gene_write"})
    if bool(policy.get("agi_completion_claim")):
        blockers.append({"code": "policy_claims_agi_completion"})

    return {
        "schema": "PggArchonGEPExternalResourceManifestValidation/v1",
        "status": _status_from_issues(blockers),
        "resource_count": len(resources),
        "blockers": blockers,
        "warnings": warnings,
        "all_untrusted": all(isinstance(item, Mapping) and item.get("trusted") is False for item in resources),
        "external_code_execution": False,
        "auto_gene_promotion": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


def build_resource_index(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    validation = validate_external_resource_manifest(manifest)
    resources = _as_list(manifest.get("resources"))
    entries = []
    for raw in resources:
        if not isinstance(raw, Mapping):
            continue
        rid = str(raw.get("id") or "")
        source_url = str(raw.get("source_url") or "")
        entries.append({
            "resource_id": rid,
            "source_hash": _stable_hash(source_url)[:16],
            "type": raw.get("type"),
            "license": raw.get("license"),
            "trusted": False,
            "execute_allowed": False,
            "allowed_use": raw.get("allowed_use"),
            "gene_candidate": False,
            "blocker": raw.get("blocker"),
        })
    index_hash = _stable_hash(json.dumps(entries, sort_keys=True, ensure_ascii=False))
    return {
        "schema": "PggArchonGEPResourceIndex/v1",
        "status": "READY" if validation["status"] == "PASS" else "BLOCK",
        "entry_count": len(entries),
        "index_hash": index_hash,
        "entries": entries,
        "manifest_validation_status": validation["status"],
        "external_code_execution": False,
        "auto_gene_promotion": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


def build_gep_resource_preflight_report(manifest: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    source = manifest if isinstance(manifest, Mapping) else build_default_external_resource_manifest()
    validation = validate_external_resource_manifest(source)
    index = build_resource_index(source)
    blockers = list(validation["blockers"])
    status = "PASS" if not blockers and index["status"] == "READY" else "BLOCK"
    substatus = "RESOURCE_PRECHECK_READY" if status == "PASS" else "RESOURCE_PRECHECK_BLOCKED"
    return {
        "schema": "PggArchonGEPResourcePreflight/v1",
        "ts": time.time(),
        "status": status,
        "substatus": substatus,
        "manifest_valid": validation["status"] == "PASS",
        "resource_count": validation["resource_count"],
        "blocked_resource_count": len(blockers),
        "warnings": validation["warnings"],
        "blockers": blockers,
        "resource_index": index,
        "external_code_execution": False,
        "credentials_detected": any(item.get("code") == "credentials_detected" for item in blockers),
        "auto_gene_promotion_detected": False,
        "auto_gene_promotion": False,
        "write_gene_allowed": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


__all__ = [
    "build_default_external_resource_manifest",
    "build_gep_resource_preflight_report",
    "build_resource_index",
    "validate_external_resource_manifest",
]
