#!/usr/bin/env python3
"""CLI for GitHub source closure gate."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_github_source_closure_gate import evaluate_github_source_cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate GitHub source closure evidence without promotion.")
    parser.add_argument("cards_json")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    cards = json.load(open(args.cards_json, encoding="utf-8"))
    if args.output_dir:
        out = evaluate_github_source_cards(cards, output_dir=args.output_dir)
    else:
        out = evaluate_github_source_cards(cards)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
