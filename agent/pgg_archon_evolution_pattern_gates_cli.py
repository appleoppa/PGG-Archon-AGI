#!/usr/bin/env python3
"""CLI for PGG internal evolution pattern gates."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_evolution_pattern_gates import evaluate_evolution_pattern_gates


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate internal PGG evolution pattern gates.")
    parser.add_argument("packet_json")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    packet = json.load(open(args.packet_json, encoding="utf-8"))
    if args.output_dir:
        out = evaluate_evolution_pattern_gates(packet, output_dir=args.output_dir)
    else:
        out = evaluate_evolution_pattern_gates(packet)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
