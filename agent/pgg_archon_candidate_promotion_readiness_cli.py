#!/usr/bin/env python3
"""CLI for PGG candidate promotion readiness gate."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_candidate_promotion_readiness import evaluate_candidate_promotion_readiness_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate candidate promotion readiness without promoting.")
    parser.add_argument("packets_json", help="JSON list of candidate readiness packets")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    packets = json.load(open(args.packets_json, encoding="utf-8"))
    if not isinstance(packets, list):
        raise SystemExit("packets_json must contain a list")
    if args.output_dir:
        out = evaluate_candidate_promotion_readiness_batch(packets, output_dir=args.output_dir)
    else:
        out = evaluate_candidate_promotion_readiness_batch(packets)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("total") == len(packets) else 2


if __name__ == "__main__":
    raise SystemExit(main())
