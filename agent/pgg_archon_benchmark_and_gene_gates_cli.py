#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from agent.pgg_archon_benchmark_and_gene_gates import evaluate_all

def main()->int:
    ap=argparse.ArgumentParser(description='PGG local benchmark and gene gates')
    ap.add_argument('packet_json'); ap.add_argument('--output-dir', default=None)
    a=ap.parse_args(); packet=json.load(open(a.packet_json,encoding='utf-8'))
    out=evaluate_all(packet, output_dir=a.output_dir)
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if out.get('status')=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
