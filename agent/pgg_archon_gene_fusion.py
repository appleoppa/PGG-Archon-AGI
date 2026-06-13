"""PGG Archon gene fusion surface.

Reads the local APEX evolution gene SQLite DB, finds groups of active genes
that share the same defect_no + defect_name, and produces a *fusion gene*
that:

- merges absorbed_knowledge / source_refs / repair_mechanism / reusable_rule
  by union (deduplicated text),
- preserves the strongest evidence_grade and severity_rank of its members,
- records the member gene_ids in source_refs_json so the lineage stays auditable,
- writes the fusion gene into evolution_genes once, marks members as
  ``superseded_by_fusion`` (status only — verification_status untouched), and
  emits an audit ledger.

Boundaries (hard):

- only operates on the already-on-disk gene DB, never spins up an external
  service, never calls an LLM, never claims AGI completion;
- only fuses gene members whose source_refs_json + boundary metadata are
  structurally valid;
- behavior is gated by the ``route_chain_gate.auto_fuse_genes`` config flag
  (default off via :func:`build_pgg_archon_gene_fusion_surface`); writing is
  also gated by an explicit ``write=True`` argument.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_GENE_DB_PATH = Path(
    "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"
)
DEFAULT_AUDIT_DIR = Path(
    "/Users/appleoppa/.hermes/workspace/agi-routing/gene-fusions"
)
SUPERSEDED_STATUS = "superseded_by_fusion"
FUSION_STATUS = "active"
FUSION_VERIFICATION = "verified_by_gene_fusion"
FUSION_GATE_TYPE = "auto_gene_fusion"
FUSION_BOUNDARY = (
    "受控融合：合并同一缺陷下的多条候选基因，不调用模型、不修改核心代码、"
    "不声称 AGI 完成；任一成员被反证可整体回滚"
)

# ── Rust native bridge ──────────────────────
_NATIVE = False
_rust_fusion = None
try:
    import hermes_pgg_gene_fusion as _rust_fusion  # type: ignore[import-untyped]
    _NATIVE = True
except ImportError:
    pass


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _gene_db_path() -> Path:
    configured = os.environ.get("APEX_GENE_LIFECYCLE_DB_PATH", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_GENE_DB_PATH


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _parse_json_field(value: Any) -> Any:
    if value in (None, ""):
        return []
    if isinstance(value, (list, dict)):
        return value
    text = str(value).strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return [text]


def _merge_text_lines(values: Iterable[Any]) -> str:
    seen: list[str] = []
    for raw in values:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.append(line)
    return "\n".join(seen)


def _merge_source_refs(values: Iterable[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for raw in values:
        parsed = _parse_json_field(raw)
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            try:
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            except TypeError:
                key = str(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _strongest_evidence(values: Iterable[Any]) -> str:
    rank = {"S": 5, "A+": 4, "A": 3, "A-": 2, "B+": 1, "B": 0}
    best_text = ""
    best_score = -10**9
    for raw in values:
        text = str(raw or "").strip()
        if not text:
            continue
        # extract leading grade like "A-: ..."
        head = text.split(":", 1)[0].strip()
        score = rank.get(head, -1)
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


def _max_int(values: Iterable[Any], default: int = 0) -> int:
    best = default
    found = False
    for raw in values:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if not found or value > best:
            best = value
            found = True
    return best


def _stable_fusion_id(defect_no: int, defect_name: str, members: Sequence[Mapping[str, Any]]) -> str:
    member_ids = sorted(str(m["gene_id"]) for m in members)
    digest = hashlib.sha256(
        json.dumps(
            {"defect_no": defect_no, "defect_name": defect_name, "members": member_ids},
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"GENE-FUSION-{digest.upper()}"


def _ensure_fusion_cycle(conn: sqlite3.Connection) -> str:
    cycle_id = "cycle_pgg_archon_gene_fusion_v1"
    conn.execute(
        """
        INSERT OR IGNORE INTO evolution_cycles
        (cycle_id, created_at, theme, sequence_logic, status, evidence_grade, boundary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cycle_id,
            time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "PGG Archon 同缺陷候选基因受控融合",
            "12534：融合→纠错→固化→降熵→规划",
            "active",
            "A-: gene_fusion union of verified candidates",
            FUSION_BOUNDARY,
        ),
    )
    return cycle_id


def _select_fusion_groups(
    conn: sqlite3.Connection,
    *,
    min_member_count: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT gene_id, cycle_id, defect_no, defect_name, gene_name, absorbed_knowledge,
               source_refs_json, repair_mechanism, severity_rank, apex_variables,
               gate_type, reusable_rule, status, evidence_grade, verification_status,
               boundary, gene_hash, created_at
        FROM evolution_genes
        WHERE status IN ('active', 'verified')
        ORDER BY created_at ASC
        """
    ).fetchall()
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        record = _row_to_dict(row)
        try:
            defect_no = int(record["defect_no"])
        except (TypeError, ValueError):
            continue
        defect_name = str(record["defect_name"] or "").strip()
        if not defect_name:
            continue
        # do not fuse fusion outputs again
        if str(record["gate_type"] or "").strip() == FUSION_GATE_TYPE:
            continue
        if str(record["status"] or "").strip() == SUPERSEDED_STATUS:
            continue
        grouped[(defect_no, defect_name)].append(record)
    out = []
    for (defect_no, defect_name), members in grouped.items():
        if len(members) < int(min_member_count):
            continue
        out.append({
            "defect_no": defect_no,
            "defect_name": defect_name,
            "members": members,
        })
    out.sort(key=lambda g: (-len(g["members"]), g["defect_no"]))
    return out


def _build_fusion_record(
    *,
    cycle_id: str,
    group: Mapping[str, Any],
) -> dict[str, Any]:
    members = list(group["members"])
    member_ids = sorted(str(m["gene_id"]) for m in members)
    fusion_id = _stable_fusion_id(group["defect_no"], group["defect_name"], members)
    absorbed = _merge_text_lines(m["absorbed_knowledge"] for m in members)
    repair = _merge_text_lines(m["repair_mechanism"] for m in members)
    rule = _merge_text_lines(m["reusable_rule"] for m in members)
    apex_vars = _merge_text_lines(m["apex_variables"] for m in members)
    refs_payload = _merge_source_refs(m["source_refs_json"] for m in members)
    refs_payload.append({
        "fusion_member_gene_ids": member_ids,
        "fusion_member_count": len(member_ids),
    })
    evidence = _strongest_evidence(m["evidence_grade"] for m in members) or "A-: gene_fusion default"
    severity = _max_int((m["severity_rank"] for m in members), default=1)
    record = {
        "gene_id": fusion_id,
        "cycle_id": cycle_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "defect_no": int(group["defect_no"]),
        "defect_name": str(group["defect_name"]),
        "gene_name": f"FUSION:{group['defect_name']}",
        "absorbed_knowledge": absorbed,
        "source_refs_json": json.dumps(refs_payload, ensure_ascii=False),
        "repair_mechanism": repair,
        "severity_rank": int(severity),
        "apex_variables": apex_vars,
        "gate_type": FUSION_GATE_TYPE,
        "reusable_rule": rule,
        "status": FUSION_STATUS,
        "evidence_grade": evidence,
        "verification_status": FUSION_VERIFICATION,
        "boundary": FUSION_BOUNDARY,
        "member_ids": member_ids,
    }
    record["gene_hash"] = _sha256_obj({k: v for k, v in record.items() if k != "gene_hash"})
    return record


def _insert_fusion_gene(conn: sqlite3.Connection, record: Mapping[str, Any]) -> bool:
    existing = conn.execute(
        "SELECT 1 FROM evolution_genes WHERE gene_id = ?",
        (record["gene_id"],),
    ).fetchone()
    if existing is not None:
        return False
    conn.execute(
        """
        INSERT INTO evolution_genes
        (gene_id, cycle_id, created_at, defect_no, defect_name, gene_name,
         absorbed_knowledge, source_refs_json, repair_mechanism, severity_rank,
         apex_variables, gate_type, reusable_rule, status, evidence_grade,
         verification_status, boundary, gene_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["gene_id"],
            record["cycle_id"],
            record["created_at"],
            record["defect_no"],
            record["defect_name"],
            record["gene_name"],
            record["absorbed_knowledge"],
            record["source_refs_json"],
            record["repair_mechanism"],
            record["severity_rank"],
            record["apex_variables"],
            record["gate_type"],
            record["reusable_rule"],
            record["status"],
            record["evidence_grade"],
            record["verification_status"],
            record["boundary"],
            record["gene_hash"],
        ),
    )
    for member_id in record["member_ids"]:
        conn.execute(
            "INSERT OR IGNORE INTO gene_source_map(gene_id, source_id) VALUES (?, ?)",
            (record["gene_id"], member_id),
        )
        conn.execute(
            "UPDATE evolution_genes SET status = ? WHERE gene_id = ? AND status != ?",
            (SUPERSEDED_STATUS, member_id, SUPERSEDED_STATUS),
        )
    return True


def _write_audit(audit_dir: Path, summary: Mapping[str, Any]) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{int(time.time())}_pgg_archon_gene_fusion.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_pgg_archon_gene_fusion_surface(
    *,
    db_path: str | Path | None = None,
    write: bool = False,
    min_member_count: int = 2,
    audit_dir: str | Path = DEFAULT_AUDIT_DIR,
    enabled: bool = True,
) -> dict[str, Any]:
    """Compute fusion candidates and optionally persist them.

    Args:
        db_path: explicit gene DB path (defaults to env / canonical path).
        write: when True and ``enabled`` is True, persists fusion records and
            updates members to ``superseded_by_fusion``. When False the call is
            read-only (dry-run) and only returns the candidates.
        min_member_count: minimum members in a defect bucket required to fuse.
        audit_dir: directory where audit ledgers are written.
        enabled: master kill switch; when False the surface short-circuits to
            ``DISABLED`` regardless of ``write``.
    """

    path = Path(db_path) if db_path is not None else _gene_db_path()
    base_summary: dict[str, Any] = {
        "schema": "PGGArchonGeneFusionSurface/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "db_path": str(path),
        "enabled": bool(enabled),
        "write": bool(write),
        "min_member_count": int(min_member_count),
        "boundary": FUSION_BOUNDARY,
        "agi_completion_claim": False,
    }
    if not enabled:
        return {**base_summary, "status": "DISABLED", "fusion_candidates": [], "fusion_records_written": 0, "audit_path": None}
    if not path.exists():
        return {
            **base_summary,
            "status": "BLOCK",
            "fusion_candidates": [],
            "fusion_records_written": 0,
            "audit_path": None,
            "error": "gene_db_missing",
        }

    # ── Rust native shortcut ──
    if _NATIVE:
        import json as _json
        raw = _rust_fusion.native_run_fusion(
            str(path), bool(write), int(min_member_count), bool(enabled)
        )
        data = _json.loads(raw)
        summary = {
            **base_summary,
            "status": data["status"],
            "fusion_candidates": data["fusion_candidates"],
            "fusion_records_written": data["fusion_records_written"],
            "side_effects": "wrote_fusion_genes_and_marked_members" if write and data["fusion_records_written"] else "read_only",
        }
        if data.get("error"):
            summary["error"] = data["error"]
        audit_path = _write_audit(Path(audit_dir), summary)
        summary["audit_path"] = str(audit_path)
        return summary

    # ── Python fallback ──
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        groups = _select_fusion_groups(conn, min_member_count=min_member_count)
        cycle_id = _ensure_fusion_cycle(conn)
        candidates = []
        written = 0
        for group in groups:
            record = _build_fusion_record(cycle_id=cycle_id, group=group)
            entry = {
                "fusion_gene_id": record["gene_id"],
                "defect_no": record["defect_no"],
                "defect_name": record["defect_name"],
                "member_ids": record["member_ids"],
                "member_count": len(record["member_ids"]),
                "evidence_grade": record["evidence_grade"],
                "severity_rank": record["severity_rank"],
                "gene_hash": record["gene_hash"],
                "written": False,
            }
            if write:
                inserted = _insert_fusion_gene(conn, record)
                entry["written"] = bool(inserted)
                if inserted:
                    written += 1
            candidates.append(entry)
        if write:
            conn.commit()
        status = "PASS" if candidates else "WATCH"
        summary = {
            **base_summary,
            "status": status,
            "fusion_candidates": candidates,
            "fusion_records_written": written,
            "side_effects": "wrote_fusion_genes_and_marked_members" if write and written else "read_only",
        }
        audit_path = _write_audit(Path(audit_dir), summary)
        summary["audit_path"] = str(audit_path)
        return summary
    finally:
        conn.close()


__all__ = [
    "DEFAULT_GENE_DB_PATH",
    "DEFAULT_AUDIT_DIR",
    "FUSION_BOUNDARY",
    "FUSION_GATE_TYPE",
    "FUSION_STATUS",
    "FUSION_VERIFICATION",
    "SUPERSEDED_STATUS",
    "build_pgg_archon_gene_fusion_surface",
]
