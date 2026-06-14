#!/usr/bin/env python3
"""CLI for PGG activation-path gene intake."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_activation_path_gene_intake import build_activation_path_gene_intake


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert uploaded AGI/evolution path notes into bounded GeneDB candidate genes.")
    parser.add_argument("source_file", help="Path to uploaded markdown/text note")
    parser.add_argument("--db-path", default=None, help="GeneDB sqlite path")
    parser.add_argument("--audit-dir", default=None, help="Audit output directory")
    parser.add_argument("--write", action="store_true", help="Insert candidate rows (never promotes)")
    parser.add_argument("--mode", choices=("coarse", "route_matrix"), default="coarse", help="Candidate template set")
    parser.add_argument("--disabled", action="store_true", help="Return DISABLED without doing work")
    args = parser.parse_args()
    kwargs = {"source_file": args.source_file, "write": args.write, "enabled": not args.disabled, "mode": args.mode}
    if args.db_path:
        kwargs["db_path"] = args.db_path
    if args.audit_dir:
        kwargs["audit_dir"] = args.audit_dir
    out = build_activation_path_gene_intake(**kwargs)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") in {"PASS", "WATCH", "DISABLED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
