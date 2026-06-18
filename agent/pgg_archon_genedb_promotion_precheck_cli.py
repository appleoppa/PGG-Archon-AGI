#!/usr/bin/env python3
"""CLI for GeneDB promotion precheck."""
from __future__ import annotations

import argparse
import json
import sqlite3

from agent.pgg_archon_genedb_promotion_precheck import evaluate_precheck_on_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GeneDB promotion precheck on candidate rows.")
    parser.add_argument("--db", default="/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
    parser.add_argument("--gate-type", default="activation_path_candidate_gene_intake", help="Filter by gate_type")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM evolution_genes WHERE gate_type = ? ORDER BY defect_no",
        (args.gate_type,),
    ).fetchall()
    con.close()
    records = [dict(r) for r in rows]
    if args.output_dir:
        out = evaluate_precheck_on_records(records, output_dir=args.output_dir)
    else:
        out = evaluate_precheck_on_records(records)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ready_count", 0) >= 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
