"""PGG Archon GeneDB schema validator.

Boundary:
- internal PGG engineering schema only, not an external authority;
- inspired by local ApexSpiral-style gene standard files but does not claim
  official ApexSpiral compliance;
- validates structure/provenance fields only, not whether a gene is true or
  effective;
- no LLM calls, no network, no database writes.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

REQUIRED_FIELDS = (
    "gene_id",
    "gene_name",
    "absorbed_knowledge",
    "source_refs_json",
    "repair_mechanism",
    "reusable_rule",
    "status",
    "evidence_grade",
    "verification_status",
    "boundary",
    "gene_hash",
)
ALLOWED_STATUS = {"candidate", "active", "verified", "retired", "superseded_by_fusion"}
BOUNDARY = (
    "internal_pgg_schema_validator; structure/provenance only; external_authority=false; "
    "does not prove gene effectiveness"
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _parse_refs(value: Any) -> tuple[list[Any], str | None]:
    if isinstance(value, list):
        return value, None
    if not isinstance(value, str) or not value.strip():
        return [], "source_refs_json_empty"
    try:
        parsed = json.loads(value)
    except Exception:
        return [], "source_refs_json_invalid_json"
    if not isinstance(parsed, list):
        return [], "source_refs_json_not_list"
    return parsed, None


def validate_gene_record(record: Mapping[str, Any], *, strict_unknown_fields: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if not str(record.get(field, "")).strip()]
    errors.extend(f"missing:{field}" for field in missing)

    status = str(record.get("status", "")).strip()
    if status and status not in ALLOWED_STATUS:
        errors.append(f"invalid_status:{status}")

    refs, refs_error = _parse_refs(record.get("source_refs_json"))
    if refs_error:
        errors.append(refs_error)

    # Evidence/provenance requirements for newly promoted/verified rows.
    verification = str(record.get("verification_status", "")).strip().lower()
    if status in {"active", "verified"} and verification in {"", "pending", "pending_review", "pending_review_activation_path_intake"}:
        errors.append("active_or_verified_requires_non_pending_verification")

    if str(record.get("external_authority", "false")).lower() == "true":
        has_external = False
        for ref in refs:
            if isinstance(ref, dict) and str(ref.get("source_type", "")).lower() in {"paper", "github", "official_doc"}:
                has_external = True
                break
        if not has_external:
            errors.append("external_authority_true_without_external_source_ref")

    boundary = str(record.get("boundary", "")).strip()
    if boundary and any(term in boundary.lower() for term in ("zero risk", "full agi", "asi completed", "零风险", "替代律师")):
        errors.append("overclaim_in_boundary")

    known = set(REQUIRED_FIELDS) | {
        "cycle_id", "created_at", "defect_no", "defect_name", "severity_rank", "apex_variables",
        "gate_type", "external_authority", "source_level", "claim_level",
    }
    unknown = sorted(set(record.keys()) - known)
    if unknown:
        if strict_unknown_fields:
            errors.extend(f"unknown_field:{field}" for field in unknown)
        else:
            warnings.extend(f"unknown_field:{field}" for field in unknown)

    return {
        "schema": "PGGGeneSchemaValidation/v1",
        "created_at": _now(),
        "gene_id": record.get("gene_id"),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "boundary": BOUNDARY,
        "external_authority": False,
    }


def validate_gene_records(records: Sequence[Mapping[str, Any]], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    evaluations = [validate_gene_record(record) for record in records]
    summary = {
        "schema": "PGGGeneSchemaValidator/v1",
        "created_at": _now(),
        "boundary": BOUNDARY,
        "total": len(evaluations),
        "valid": sum(1 for ev in evaluations if ev["valid"]),
        "invalid": sum(1 for ev in evaluations if not ev["valid"]),
        "evaluations": evaluations,
    }
    if output_dir is not None:
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(json.dumps(summary, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
        path = out_dir / f"{int(time.time())}_gene_schema_validator_{digest}.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["output_path"] = str(path)
    return summary


__all__ = ["BOUNDARY", "REQUIRED_FIELDS", "validate_gene_record", "validate_gene_records"]
