"""PGG GeneDB quality gate.

Read-only gate for detecting inflated/low-confidence evolution genes.
It does not promote, retire, or mutate genes.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"


def _rows(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def build_status(db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        return {"schema": "PGGGeneQualityGate/v1", "status": "ERROR_DB_MISSING", "db": str(db_path)}
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    total = _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes")[0]["c"]
    by_status = _rows(cur, "SELECT status, COUNT(*) AS c FROM evolution_genes GROUP BY status ORDER BY c DESC")
    low_verified = _rows(cur, """
        SELECT gene_id,gene_name,gate_type,status,verification_status,fitness,
               substr(absorbed_knowledge,1,160) AS sample
        FROM evolution_genes
        WHERE status='verified' AND COALESCE(fitness,0) < 300
        ORDER BY COALESCE(fitness,0) ASC, created_at DESC
        LIMIT 25
    """)
    high_dream = _rows(cur, """
        SELECT gene_id,gene_name,gate_type,status,verification_status,fitness,
               substr(absorbed_knowledge,1,160) AS sample
        FROM evolution_genes
        WHERE gene_id LIKE 'dream_auto_fusion_%' AND COALESCE(fitness,0) > 5000
        ORDER BY COALESCE(fitness,0) DESC
        LIMIT 25
    """)
    candidate_by_gate = _rows(cur, """
        SELECT gate_type, COUNT(*) AS c
        FROM evolution_genes
        WHERE status='candidate'
        GROUP BY gate_type ORDER BY c DESC LIMIT 20
    """)
    counts = {
        "low_fitness_verified": _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes WHERE status='verified' AND COALESCE(fitness,0)<300")[0]["c"],
        "high_fitness_dream_auto_fusion": _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes WHERE gene_id LIKE 'dream_auto_fusion_%' AND COALESCE(fitness,0)>5000")[0]["c"],
        "candidate_backlog": _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes WHERE status='candidate'")[0]["c"],
        "rule_reviewed_verified": _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes WHERE status='verified' AND verification_status LIKE '%rule_reviewed%'")[0]["c"],
        "llm_reviewed_verified": _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes WHERE status='verified' AND verification_status LIKE '%llm%'")[0]["c"],
    }
    con.close()
    blockers = []
    watch = []
    if counts["low_fitness_verified"] > 0:
        watch.append("LOW_FITNESS_VERIFIED_REVIEW_REQUIRED")
    if counts["high_fitness_dream_auto_fusion"] > 0:
        watch.append("DREAM_FITNESS_INFLATION_REVIEW_REQUIRED")
    if counts["candidate_backlog"] > 200:
        watch.append("CANDIDATE_BACKLOG_GT_200")
    status = "PASS" if not watch and not blockers else "WATCH_GENE_QUALITY_REVIEW_REQUIRED"
    return {
        "schema": "PGGGeneQualityGate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "db": str(db_path),
        "total": total,
        "by_status": by_status,
        "counts": counts,
        "candidate_by_gate": candidate_by_gate,
        "low_fitness_verified_samples": low_verified,
        "high_fitness_dream_samples": high_dream,
        "watch": watch,
        "blockers": blockers,
        "recommended_actions": [
            "sample-review low_fitness_verified before any status mutation",
            "cap or normalize dream_auto_fusion fitness only after evidence audit",
            "process candidate backlog through bridge_processor; do not auto-promote",
        ],
        "boundary": "Read-only quality gate; no promotion/retirement/mutation; not AGI/T5 proof.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    status = build_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"{status['status']} total={status.get('total')} counts={status.get('counts')}")
    return 0 if str(status.get("status", "")).startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
