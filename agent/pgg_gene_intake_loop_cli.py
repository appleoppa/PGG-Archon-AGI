#!/usr/bin/env python3
"""PGG Gene Intake Loop CLI — automated candidate gene pipeline."""

from __future__ import annotations
import argparse, json
from agent.pgg_gene_intake_loop import run_intake_loop


def main() -> int:
    ap = argparse.ArgumentParser(description='PGG Gene Intake Loop: scan→dedup→score→fusion dry-run→packet')
    ap.add_argument('--write', action='store_true', help='Write new candidates to GeneDB (default dry-run)')
    ap.add_argument('--top-n', type=int, default=5, help='Top-N for fusion dry-run (default 5)')
    ap.add_argument('--json-only', action='store_true', help='Compact one-line JSON output')
    args = ap.parse_args()

    out = run_intake_loop(
        write_candidates=args.write,
        top_n=args.top_n,
    )
    if args.json_only:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get('status') in {'PASS_NO_NEW_CANDIDATES', 'PASS_NEW_CANDIDATES'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
