#!/usr/bin/env python3
"""CLI for PGG GeneDB schema validator."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_gene_schema_validator import validate_gene_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GeneDB-like records structurally without proving truth/effectiveness.")
    parser.add_argument("records_json", help="JSON file containing a list of gene records")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    records = json.load(open(args.records_json, encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("records_json must contain a list")
    if args.output_dir:
        out = validate_gene_records(records, output_dir=args.output_dir)
    else:
        out = validate_gene_records(records)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("invalid", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
