"""PGG GeneDB quality gate.

Blocking gate for detecting inflated/low-confidence evolution genes.
It does not promote, retire, or mutate genes, but it returns BLOCK when
GeneDB content is unsafe for promotion/fusion.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("/Users/appleoppa/.hermes/data/pgg_archon.db")


def _rows(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _table_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    return {str(r[1]) for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _first_existing(cols: set[str], *names: str, default: str = "NULL") -> str:
    for name in names:
        if name in cols:
            return name
    return default


def build_status(db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        return {"schema": "PGGGeneQualityGate/v1", "status": "ERROR_DB_MISSING", "db": str(db_path)}
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    eg_cols = _table_columns(cur, "evolution_genes")
    gene_cols = _table_columns(cur, "genes")
    status_col = _first_existing(eg_cols, "status", "state", default="''")
    fitness_col = _first_existing(eg_cols, "fitness", "fitness_after", "fitness_before", default="0")
    name_col = _first_existing(eg_cols, "gene_name", default="CAST(eg.gene_id AS TEXT)")
    gate_col = _first_existing(eg_cols, "gate_type", "mutation_vector", default="''")
    verification_col = _first_existing(eg_cols, "verification_status", default="''")
    absorbed_col = _first_existing(eg_cols, "absorbed_knowledge", "evidence_ref", default="''")
    created_col = _first_existing(eg_cols, "created_at", "promoted_at", default="eg.gene_id")
    auto_fusion_where = (
        "(g.pattern_type='auto_fusion' OR eg.mutation_vector='auto_fusion')"
        if "mutation_vector" in eg_cols else "g.pattern_type='auto_fusion'"
    )

    total = _rows(cur, "SELECT COUNT(*) AS c FROM evolution_genes")[0]["c"]
    by_status = _rows(cur, f"SELECT {status_col} AS status, COUNT(*) AS c FROM evolution_genes GROUP BY {status_col} ORDER BY c DESC")
    low_verified = _rows(cur, f"""
        SELECT eg.gene_id,{name_col} AS gene_name,{gate_col} AS gate_type,{status_col} AS status,
               {verification_col} AS verification_status,{fitness_col} AS fitness,
               substr({absorbed_col},1,160) AS sample
        FROM evolution_genes eg
        WHERE {status_col}='verified' AND COALESCE({fitness_col},0) < 300
        ORDER BY COALESCE({fitness_col},0) ASC, {created_col} DESC
        LIMIT 25
    """)
    high_dream = _rows(cur, f"""
        SELECT eg.gene_id,{name_col} AS gene_name,{gate_col} AS gate_type,{status_col} AS status,
               {verification_col} AS verification_status,{fitness_col} AS fitness,
               substr({absorbed_col},1,160) AS sample
        FROM evolution_genes eg
        LEFT JOIN genes g ON CAST(eg.gene_id AS TEXT)=CAST(g.id AS TEXT)
        WHERE ({auto_fusion_where} OR CAST(eg.gene_id AS TEXT) LIKE 'dream_auto_fusion_%')
          AND COALESCE({fitness_col},0) > 5000
        ORDER BY COALESCE({fitness_col},0) DESC
        LIMIT 25
    """)
    candidate_by_gate = _rows(cur, f"""
        SELECT {gate_col} AS gate_type, COUNT(*) AS c
        FROM evolution_genes
        WHERE {status_col}='candidate'
        GROUP BY {gate_col} ORDER BY c DESC LIMIT 20
    """)
    empty_code_samples = _rows(cur, """
        SELECT g.id AS gene_id, g.name, g.pattern_type, gl.state, g.quality_score
        FROM genes g
        LEFT JOIN gene_lifecycle gl ON CAST(gl.gene_id AS TEXT)=CAST(g.id AS TEXT)
        WHERE COALESCE(TRIM(g.code_snippet),'') = ''
          AND COALESCE(gl.state, 'candidate') IN ('candidate','promoted','active')
        ORDER BY COALESCE(g.quality_score,0) DESC
        LIMIT 25
    """) if "code_snippet" in gene_cols else []
    counts = {
        "low_fitness_verified": _rows(cur, f"SELECT COUNT(*) AS c FROM evolution_genes WHERE {status_col}='verified' AND COALESCE({fitness_col},0)<300")[0]["c"],
        "high_fitness_dream_auto_fusion": _rows(cur, f"""
            SELECT COUNT(*) AS c
            FROM evolution_genes eg
            LEFT JOIN genes g ON CAST(eg.gene_id AS TEXT)=CAST(g.id AS TEXT)
            WHERE ({auto_fusion_where} OR CAST(eg.gene_id AS TEXT) LIKE 'dream_auto_fusion_%')
              AND COALESCE({fitness_col},0)>5000
        """)[0]["c"],
        "candidate_backlog": _rows(cur, f"SELECT COUNT(*) AS c FROM evolution_genes WHERE {status_col}='candidate'")[0]["c"],
        "empty_code_snippet_active_or_candidate": _rows(cur, """
            SELECT COUNT(*) AS c
            FROM genes g
            LEFT JOIN gene_lifecycle gl ON CAST(gl.gene_id AS TEXT)=CAST(g.id AS TEXT)
            WHERE COALESCE(TRIM(g.code_snippet),'') = ''
              AND COALESCE(gl.state, 'candidate') IN ('candidate','promoted','active')
        """)[0]["c"] if "code_snippet" in gene_cols else 0,
        "rule_reviewed_verified": _rows(cur, f"SELECT COUNT(*) AS c FROM evolution_genes WHERE {status_col}='verified' AND {verification_col} LIKE '%rule_reviewed%'")[0]["c"],
        "llm_reviewed_verified": _rows(cur, f"SELECT COUNT(*) AS c FROM evolution_genes WHERE {status_col}='verified' AND {verification_col} LIKE '%llm%'")[0]["c"],
    }
    con.close()
    blockers = []
    watch = []
    if counts["low_fitness_verified"] > 0:
        watch.append("LOW_FITNESS_VERIFIED_REVIEW_REQUIRED")
    if counts["high_fitness_dream_auto_fusion"] > 0:
        blockers.append("DREAM_FITNESS_INFLATION_BLOCKED")
    if counts["empty_code_snippet_active_or_candidate"] > 0:
        blockers.append("EMPTY_CODE_SNIPPET_BLOCKED")
    if counts["candidate_backlog"] > 200:
        watch.append("CANDIDATE_BACKLOG_GT_200")
    status = "PASS" if not watch and not blockers else "BLOCK_GENE_QUALITY_REVIEW_REQUIRED" if blockers else "WATCH_GENE_QUALITY_REVIEW_REQUIRED"
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
        "empty_code_snippet_samples": empty_code_samples,
        "watch": watch,
        "blockers": blockers,
        "recommended_actions": [
            "sample-review low_fitness_verified before any status mutation",
            "block and repair dream/auto_fusion fitness inflation before promotion",
            "populate or retire genes with empty code_snippet before fusion/promotion",
            "process candidate backlog through bridge_processor; do not auto-promote",
        ],
        "boundary": "Blocking quality gate; no promotion/retirement/mutation; not AGI/T5 proof.",
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
