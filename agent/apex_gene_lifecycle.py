"""APEX RuntimeOS gene lifecycle gate.

The gate validates gene lifecycle metadata before any future promotion path may
claim durable evolution.  It is read-only and aggregate-safe: no gene database,
memory store, or file is mutated by this module.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

ALLOWED_GENE_STATUSES = ("active", "verified", "retired")
PROMOTABLE_STATUSES = ("verified",)


class GeneLifecycleValidationError(ValueError):
    """Raised when gene lifecycle metadata is structurally invalid."""


def normalize_gene_status(status: Any) -> str:
    text = str(status or "").strip().lower()
    if text not in ALLOWED_GENE_STATUSES:
        raise GeneLifecycleValidationError(f"unknown gene lifecycle status: {text or '<empty>'}")
    return text


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def build_gene_lifecycle_gate_report(genes: Sequence[Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    """Validate lifecycle metadata for a batch of gene candidates.

    Required safe fields per item:
    - gene or id
    - status: active | verified | retired
    - evidence_hash or evidence
    - validation_passed or verified_at for verified genes
    - retirement_reason for retired genes
    """
    items = list(genes or [])
    issues: list[Dict[str, Any]] = []
    counts = {status: 0 for status in ALLOWED_GENE_STATUSES}
    promotable = 0
    normalized = []
    seen_ids: set[str] = set()

    for idx, raw in enumerate(items):
        if not isinstance(raw, Mapping):
            issues.append({"code": "malformed_gene", "index": idx})
            continue
        gene_id = str(raw.get("gene") or raw.get("id") or "").strip()
        if not gene_id:
            issues.append({"code": "missing_gene_id", "index": idx})
            gene_id = f"<missing:{idx}>"
        if gene_id in seen_ids:
            issues.append({"code": "duplicate_gene_id", "gene": gene_id})
        seen_ids.add(gene_id)
        try:
            status = normalize_gene_status(raw.get("status"))
        except GeneLifecycleValidationError as exc:
            issues.append({"code": "invalid_status", "gene": gene_id, "message": str(exc)})
            continue
        counts[status] += 1
        has_evidence = _has_text(raw.get("evidence_hash")) or _has_text(raw.get("evidence")) or _has_text(raw.get("last_report"))
        validation_passed = bool(raw.get("validation_passed")) or _has_text(raw.get("verified_at"))
        retirement_reason = _has_text(raw.get("retirement_reason")) or _has_text(raw.get("replaced_by"))

        if not has_evidence:
            issues.append({"code": "missing_evidence", "gene": gene_id, "status": status})
        if status == "verified" and not validation_passed:
            issues.append({"code": "verified_without_validation", "gene": gene_id})
        if status == "retired" and not retirement_reason:
            issues.append({"code": "retired_without_reason", "gene": gene_id})
        if status == "active" and validation_passed:
            issues.append({"code": "active_has_validation_but_not_verified", "gene": gene_id})
        can_promote = status in PROMOTABLE_STATUSES and has_evidence and validation_passed
        if can_promote:
            promotable += 1
        normalized.append({
            "gene": gene_id,
            "status": status,
            "has_evidence": has_evidence,
            "validation_passed": validation_passed,
            "promotable": can_promote,
        })

    if not items:
        issues.append({"code": "no_gene_candidates"})
    status = "PASS" if items and not issues else ("WARN" if normalized else "BLOCK")
    return {
        "schema": "ApexRuntimeOSGeneLifecycleGate/v1",
        "status": status,
        "allowed_statuses": list(ALLOWED_GENE_STATUSES),
        "promotable_statuses": list(PROMOTABLE_STATUSES),
        "gene_count": len(normalized),
        "counts": counts,
        "promotable_count": promotable,
        "issues": issues,
        "genes": normalized[:50],
        "side_effects": "read_only_report",
    }


def build_gene_lifecycle_gate_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose lifecycle readiness without scanning private gene stores.

    The autonomy summary currently has no explicit gene-candidate evidence, so
    the safe default is BLOCK instead of pretending lifecycle validation exists.
    """
    return build_gene_lifecycle_gate_report([])


__all__ = [
    "ALLOWED_GENE_STATUSES",
    "PROMOTABLE_STATUSES",
    "GeneLifecycleValidationError",
    "build_gene_lifecycle_gate_from_runtimeos_status",
    "build_gene_lifecycle_gate_report",
    "normalize_gene_status",
]
