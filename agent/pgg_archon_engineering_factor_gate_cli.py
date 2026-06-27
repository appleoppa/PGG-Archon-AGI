#!/usr/bin/env python3
"""CLI for PGG engineering factor gate."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_engineering_factor_gate import evaluate_engineering_factor_cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate engineering factor cards for pattern-only absorption.")
    parser.add_argument("cards_json")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    cards = json.load(open(args.cards_json, encoding="utf-8"))
    if args.output_dir:
        out = evaluate_engineering_factor_cards(cards, output_dir=args.output_dir)
    else:
        out = evaluate_engineering_factor_cards(cards)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("invalid", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
