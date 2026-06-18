#!/usr/bin/env python3
"""
PGG GeneDB candidate→active promotion gate.

Default mode is read-only dry-run.  The executable path is intentionally small and
batch-limited: only candidate rows with fitness_after > 80 and a non-empty
parent_gene_id are eligible, and each run can promote at most 10 rows.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path.home() / ".hermes/data/pgg_archon.db"
DEFAULT_LOG = Path.home() / ".hermes/logs/pgg_genedb_promote.log"
MAX_BATCH = 10


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def ensure_runtime_schema(conn: sqlite3.Connection) -> None:
    cols = {
        r["name"]
        for r in conn.execute("PRAGMA table_info(evolution_genes)").fetchall()
    }
    required = {"id", "gene_id", "parent_gene_id", "state", "fitness_after", "promoted_at"}
    missing = sorted(required - cols)
    if missing:
        raise RuntimeError(f"evolution_genes schema missing required columns: {missing}")


def fetch_candidates(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, gene_id, parent_gene_id, state,
               fitness_before, fitness_after, evidence_ref, created_at
        FROM evolution_genes
        WHERE state = 'candidate'
          AND fitness_after > 80.0
          AND parent_gene_id IS NOT NULL
          AND CAST(parent_gene_id AS TEXT) != ''
        ORDER BY fitness_after DESC, id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def summarize(conn: sqlite3.Connection) -> dict[str, Any]:
    by_state = [
        row_to_dict(r)
        for r in conn.execute(
            """
            SELECT state,
                   COUNT(*) AS count,
                   ROUND(MIN(fitness_after), 4) AS min_fitness_after,
                   ROUND(MAX(fitness_after), 4) AS max_fitness_after,
                   SUM(CASE WHEN parent_gene_id IS NOT NULL
                             AND CAST(parent_gene_id AS TEXT) != '' THEN 1 ELSE 0 END) AS with_parent,
                   SUM(CASE WHEN evidence_ref IS NOT NULL AND evidence_ref != '' THEN 1 ELSE 0 END) AS with_evidence
            FROM evolution_genes
            GROUP BY state
            ORDER BY state
            """
        ).fetchall()
    ]
    eligible_total = conn.execute(
        """
        SELECT COUNT(*)
        FROM evolution_genes
        WHERE state = 'candidate'
          AND fitness_after > 80.0
          AND parent_gene_id IS NOT NULL
          AND CAST(parent_gene_id AS TEXT) != ''
        """
    ).fetchone()[0]
    return {"by_state": by_state, "eligible_total": eligible_total}


def append_log(log_path: Path, event: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def promote(db_path: Path, *, dry_run: bool, limit: int, log_path: Path) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    if limit > MAX_BATCH:
        raise ValueError(f"--limit must be <= {MAX_BATCH}; refusing bulk promotion")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_runtime_schema(conn)
        summary_before = summarize(conn)
        rows = fetch_candidates(conn, limit)
        candidates = [row_to_dict(r) for r in rows]
        now = utc_now()
        result: dict[str, Any] = {
            "schema": "PGGGeneDBPromoteGate/v1",
            "generated_at": now,
            "db": str(db_path),
            "dry_run": dry_run,
            "limit": limit,
            "eligible_total": summary_before["eligible_total"],
            "selected_count": len(candidates),
            "selected": candidates,
            "summary_before": summary_before,
            "mutations": [],
            "boundary": "candidate→active gate; default dry-run; max 10 rows; no mutation unless --no-dry-run is explicitly passed",
        }

        if not dry_run and candidates:
            conn.execute("BEGIN")
            try:
                for item in candidates:
                    conn.execute(
                        "UPDATE evolution_genes SET state = 'active', promoted_at = ? "
                        "WHERE id = ? AND state = 'candidate'",
                        (now, item["id"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO gene_lifecycle
                            (gene_id, state, activated_at, promoted_at, quality_score, parent_gene_id, candidate_at)
                        VALUES (?, 'active', ?, ?, ?, ?, ?)
                        ON CONFLICT(gene_id) DO UPDATE SET
                            state = 'active',
                            activated_at = COALESCE(gene_lifecycle.activated_at, excluded.activated_at),
                            promoted_at = excluded.promoted_at,
                            quality_score = excluded.quality_score,
                            parent_gene_id = excluded.parent_gene_id
                        """,
                        (
                            item["gene_id"],
                            now,
                            now,
                            item["fitness_after"],
                            item["parent_gene_id"],
                            item["created_at"],
                        ),
                    )
                    result["mutations"].append({
                        "id": item["id"],
                        "gene_id": item["gene_id"],
                        "from": "candidate",
                        "to": "active",
                        "promoted_at": now,
                    })
                conn.commit()
                result["promoted_count"] = len(result["mutations"])
            except Exception:
                conn.rollback()
                raise
        else:
            result["promoted_count"] = 0

        append_log(log_path, {
            "ts": now,
            "event": "pgg_genedb_promote",
            "dry_run": dry_run,
            "db": str(db_path),
            "eligible_total": result["eligible_total"],
            "selected_count": result["selected_count"],
            "promoted_count": result["promoted_count"],
            "selected_ids": [x["id"] for x in candidates],
        })
        return result
    finally:
        conn.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PGG GeneDB candidate→active promotion gate (dry-run by default)."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB path")
    parser.add_argument("--log", default=str(DEFAULT_LOG), help="JSONL promotion log path")
    parser.add_argument("--limit", type=int, default=MAX_BATCH, help=f"Batch size, max {MAX_BATCH}")
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually promote selected rows. Default is read-only dry-run.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    dry_run = not args.no_dry_run
    result = promote(Path(args.db).expanduser(), dry_run=dry_run, limit=args.limit, log_path=Path(args.log).expanduser())

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Dry-run={result['dry_run']}")
    print(f"Eligible candidate→active: {result['eligible_total']}")
    print(f"Selected this batch: {result['selected_count']} / limit={result['limit']}")
    print(f"Promoted: {result['promoted_count']}")
    if result["selected"]:
        preview = [x["id"] for x in result["selected"][:10]]
        print(f"Selected IDs: {preview}")
    print(f"Log: {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
