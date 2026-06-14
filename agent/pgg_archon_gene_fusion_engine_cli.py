#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from agent.pgg_archon_gene_fusion_engine import fuse_genedb_records, insert_fused_gene

def main() -> int:
    ap = argparse.ArgumentParser(description='PGG standard gene fusion engine')
    ap.add_argument('--parents', nargs='*', default=[])
    ap.add_argument('--gene-json')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--promote', action='store_true')
    ap.add_argument('--mode', choices=['additive','multiplicative'], default='additive')
    args = ap.parse_args()
    if args.gene_json:
        data = json.load(open(args.gene_json, encoding='utf-8'))
        out = insert_fused_gene(data, write=args.write, promote=args.promote)
        ok = out.get('status') in {'PASS', 'DRY_RUN'}
    else:
        out = fuse_genedb_records(args.parents, write=args.write, promote=args.promote, mode=args.mode)
        ok = out.get('fusion', {}).get('status') == 'PASS'
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 2

if __name__ == '__main__':
    raise SystemExit(main())
