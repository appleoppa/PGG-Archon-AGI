"""APEX RuntimeOS gene lifecycle gate.

The gate validates gene lifecycle metadata before any future promotion path may
claim durable evolution.  It is read-only and aggregate-safe: no gene database,
memory store, or file is mutated by this module.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

ALLOWED_GENE_STATUSES = ("active", "verified", "retired")
PROMOTABLE_STATUSES = ("verified",)
DEFAULT_GENE_DB_PATH = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")


class GeneLifecycleValidationError(ValueError):
    """Raised when gene lifecycle metadata is structurally invalid."""


def normalize_gene_status(status: Any) -> str:
    text = str(status or "").strip().lower()
    if text in ALLOWED_GENE_STATUSES:
        return text
    # The historical SQLite schema has both status and verification_status.
    # Keep lifecycle names strict, but accept verified-ish verification values as
    # an input mapping when reading existing records.
    if text in {"passed", "pass", "ok", "validated", "verification_passed"}:
        return "verified"
    if text in {"deprecated", "disabled", "archived", "replaced"}:
        return "retired"
    raise GeneLifecycleValidationError(f"unknown gene lifecycle status: {text or '<empty>'}")


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _gene_db_path() -> Path:
    configured = os.environ.get("APEX_GENE_LIFECYCLE_DB_PATH", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_GENE_DB_PATH


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (table,)).fetchone()
    return row is not None


def _is_verified_status(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text in {"verified", "passed", "pass", "ok", "validated", "verification_passed"} or text.startswith("verified_")


def _map_sqlite_gene(row: sqlite3.Row) -> Dict[str, Any]:
    raw_status = str(row["status"] or "").strip().lower()
    verification = str(row["verification_status"] or "").strip().lower() if "verification_status" in row.keys() else ""
    lifecycle_status = raw_status
    if _is_verified_status(verification):
        lifecycle_status = "verified"
    elif raw_status not in ALLOWED_GENE_STATUSES:
        lifecycle_status = raw_status
    return {
        "gene": row["gene_id"],
        "status": lifecycle_status,
        "evidence_hash": row["gene_hash"],
        "evidence": row["evidence_grade"],
        "validation_passed": _is_verified_status(verification),
        "verified_at": row["created_at"] if _is_verified_status(verification) else "",
        "retirement_reason": row["boundary"] if lifecycle_status == "retired" else "",
        "source_table": row["source_table"],
    }


def load_gene_lifecycle_candidates_from_sqlite(db_path: Path | None = None, *, limit: int = 500) -> Dict[str, Any]:
    """Read gene lifecycle candidates from the local APEX gene SQLite DB.

    Read-only guarantees:
    - opens SQLite in immutable read-only URI mode;
    - returns only aggregate/sanitized metadata fields;
    - never writes, migrates, or creates tables.
    """
    path = Path(db_path) if db_path is not None else _gene_db_path()
    if not path.exists():
        return {
            "schema": "ApexRuntimeOSGeneLifecycleSQLiteRead/v1",
            "status": "BLOCK",
            "db_exists": False,
            "source_table": None,
            "genes": [],
            "error": "db_missing",
            "side_effects": "read_only_report",
        }
    uri = f"file:{path}?mode=ro&immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            if _table_exists(conn, "evolution_genes"):
                table = "evolution_genes"
            elif _table_exists(conn, "genes"):
                table = "genes"
            else:
                return {
                    "schema": "ApexRuntimeOSGeneLifecycleSQLiteRead/v1",
                    "status": "BLOCK",
                    "db_exists": True,
                    "source_table": None,
                    "genes": [],
                    "error": "gene_table_missing",
                    "side_effects": "read_only_report",
                }
            rows = conn.execute(
                f"""
                SELECT gene_id, status, evidence_grade, verification_status, boundary, gene_hash, created_at,
                       ? AS source_table
                FROM {table}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (table, max(1, min(int(limit), 5000))),
            ).fetchall()
            genes = [_map_sqlite_gene(row) for row in rows]
            return {
                "schema": "ApexRuntimeOSGeneLifecycleSQLiteRead/v1",
                "status": "PASS" if genes else "BLOCK",
                "db_exists": True,
                "source_table": table,
                "gene_count": len(genes),
                "genes": genes,
                "side_effects": "read_only_report",
            }
        finally:
            conn.close()
    except Exception as exc:
        return {
            "schema": "ApexRuntimeOSGeneLifecycleSQLiteRead/v1",
            "status": "ERROR",
            "db_exists": True,
            "source_table": None,
            "genes": [],
            "error": type(exc).__name__,
            "side_effects": "read_only_report",
        }


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


def _co_scientist_candidate_to_gene(candidate: Mapping[str, Any]) -> Dict[str, Any] | None:
    """Map a read-only Co-Scientist gene candidate into lifecycle metadata."""
    if candidate.get("schema") != "ApexCoScientistGeneCandidateSummary/v1":
        return None
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    if not candidate_id:
        return None
    eligible = bool(candidate.get("eligible")) and str(candidate.get("status") or "") == "READY"
    return {
        "gene": f"co_scientist:{candidate_id}",
        "status": "verified" if eligible else "active",
        "evidence_hash": candidate_id,
        "evidence": str(candidate.get("evidence_level") or "co_scientist_candidate"),
        "validation_passed": eligible,
        "verified_at": "co_scientist_candidate_ready" if eligible else "",
        "source": "co_scientist_gene_candidate",
    }


def _archon_absorption_candidate_to_gene(candidate: Mapping[str, Any]) -> Dict[str, Any] | None:
    """Map a guarded PGG Archon absorption candidate into lifecycle metadata."""
    if candidate.get("schema") != "PGGArchonGuardedAbsorptionGene/v1":
        return None
    candidate_id = str(candidate.get("gene_id") or "").strip()
    if not candidate_id:
        return None
    eligible = bool(candidate.get("eligible")) and str(candidate.get("status") or "") == "READY"
    return {
        "gene": f"archon_absorption:{candidate_id}",
        "status": "verified" if eligible else "active",
        "evidence_hash": candidate_id,
        "evidence": str(candidate.get("evidence_level") or "guarded_absorption_candidate"),
        "validation_passed": eligible,
        "verified_at": "guarded_absorption_candidate_ready" if eligible else "",
        "source": "pgg_archon_guarded_absorption_candidate",
    }


def build_gene_lifecycle_gate_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose lifecycle readiness from the local gene DB and read-only candidates."""
    db_read = load_gene_lifecycle_candidates_from_sqlite(limit=500)
    raw_genes_any = db_read.get("genes")
    raw_genes = raw_genes_any if isinstance(raw_genes_any, list) else []
    genes: list[Mapping[str, Any]] = [item for item in raw_genes if isinstance(item, Mapping)]
    co_gene_raw = status.get("co_scientist_gene_candidate") if isinstance(status, Mapping) else None
    co_gene: Mapping[str, Any] = co_gene_raw if isinstance(co_gene_raw, Mapping) else {}
    co_lifecycle_gene = _co_scientist_candidate_to_gene(co_gene)
    if co_lifecycle_gene:
        genes.append(co_lifecycle_gene)
    absorption_gene_raw = status.get("archon_absorption_gene_candidate") if isinstance(status, Mapping) else None
    absorption_gene: Mapping[str, Any] = absorption_gene_raw if isinstance(absorption_gene_raw, Mapping) else {}
    absorption_lifecycle_gene = _archon_absorption_candidate_to_gene(absorption_gene)
    if absorption_lifecycle_gene:
        genes.append(absorption_lifecycle_gene)
    report = build_gene_lifecycle_gate_report(genes)
    report["sqlite_read"] = {
        "schema": db_read.get("schema"),
        "status": db_read.get("status"),
        "db_exists": db_read.get("db_exists"),
        "source_table": db_read.get("source_table"),
        "gene_count": db_read.get("gene_count", 0),
        "side_effects": "read_only_report",
    }
    report["co_scientist_gene_candidate"] = {
        "present": bool(co_lifecycle_gene),
        "status": co_gene.get("status", "UNKNOWN") if co_gene else "UNKNOWN",
        "eligible": bool(co_gene.get("eligible")) if co_gene else False,
        "gene_library_written": bool(co_gene.get("gene_library_written")) if co_gene else False,
        "side_effects": "read_only_report",
    }
    report["archon_absorption_gene_candidate"] = {
        "present": bool(absorption_lifecycle_gene),
        "status": absorption_gene.get("status", "UNKNOWN") if absorption_gene else "UNKNOWN",
        "eligible": bool(absorption_gene.get("eligible")) if absorption_gene else False,
        "gene_library_written": bool(absorption_gene.get("gene_library_written")) if absorption_gene else False,
        "side_effects": "read_only_report",
    }
    return report


def classify_gene_lifecycle_issues(genes: Sequence[Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    """Classify lifecycle issues into low-risk remediation buckets.

    The function is intentionally read-only and returns hashes/IDs only; it does
    not rewrite statuses or evidence fields.
    """
    report = build_gene_lifecycle_gate_report(genes)
    buckets: Dict[str, Dict[str, Any]] = {}
    for issue in report.get("issues", []):
        if not isinstance(issue, Mapping):
            continue
        code = str(issue.get("code") or "unknown")
        bucket = buckets.setdefault(code, {"code": code, "count": 0, "sample_genes": []})
        bucket["count"] += 1
        gene = str(issue.get("gene") or "")
        if gene and len(bucket["sample_genes"]) < 10:
            bucket["sample_genes"].append(gene)
    remediation = []
    if "active_has_validation_but_not_verified" in buckets:
        remediation.append({
            "code": "promote_verified_status",
            "risk": "medium",
            "action": "active + validation_passed 的基因可候选改为 verified；执行前必须备份并逐条读回验证",
            "affected_count": buckets["active_has_validation_but_not_verified"]["count"],
        })
    if "verified_without_validation" in buckets:
        remediation.append({
            "code": "hold_unvalidated_verified",
            "risk": "medium",
            "action": "verified 但缺验证证据的基因应降级 HOLD 或补验证证据；不能自动通过",
            "affected_count": buckets["verified_without_validation"]["count"],
        })
    if "missing_evidence" in buckets:
        remediation.append({
            "code": "fill_or_hold_missing_evidence",
            "risk": "medium",
            "action": "缺证据的基因必须补 evidence_hash/evidence 或保持 HOLD",
            "affected_count": buckets["missing_evidence"]["count"],
        })
    if "retired_without_reason" in buckets:
        remediation.append({
            "code": "add_retirement_reason",
            "risk": "low",
            "action": "retired 基因补 retirement_reason/replaced_by 来源；不改变运行状态",
            "affected_count": buckets["retired_without_reason"]["count"],
        })
    return {
        "schema": "ApexRuntimeOSGeneLifecycleIssueClassification/v1",
        "status": "OK" if not buckets else "WATCH",
        "gate_status": report.get("status"),
        "gene_count": report.get("gene_count", 0),
        "issue_bucket_count": len(buckets),
        "issue_buckets": sorted(buckets.values(), key=lambda item: int(item.get("count") or 0), reverse=True),
        "remediation_candidates": remediation,
        "side_effects": "read_only_report",
    }


def classify_gene_lifecycle_issues_from_sqlite(db_path: Path | None = None, *, limit: int = 500) -> Dict[str, Any]:
    read = load_gene_lifecycle_candidates_from_sqlite(db_path, limit=limit)
    classification = classify_gene_lifecycle_issues(read.get("genes") if isinstance(read.get("genes"), list) else [])
    classification["sqlite_read"] = {
        "schema": read.get("schema"),
        "status": read.get("status"),
        "db_exists": read.get("db_exists"),
        "source_table": read.get("source_table"),
        "gene_count": read.get("gene_count", 0),
        "side_effects": "read_only_report",
    }
    return classification


__all__ = [
    "ALLOWED_GENE_STATUSES",
    "DEFAULT_GENE_DB_PATH",
    "PROMOTABLE_STATUSES",
    "GeneLifecycleValidationError",
    "build_gene_lifecycle_gate_from_runtimeos_status",
    "build_gene_lifecycle_gate_report",
    "classify_gene_lifecycle_issues",
    "classify_gene_lifecycle_issues_from_sqlite",
    "load_gene_lifecycle_candidates_from_sqlite",
    "normalize_gene_status",
]
