#!/usr/bin/env python3
"""CLI for PGG source evidence gate."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_source_evidence_gate import evaluate_evidence_cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate PGG evolution source evidence cards without promotion.")
    parser.add_argument("cards_json", help="JSON file containing a list of evidence cards")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    cards = json.load(open(args.cards_json, encoding="utf-8"))
    if not isinstance(cards, list):
        raise SystemExit("cards_json must contain a list")
    if args.output_dir:
        out = evaluate_evidence_cards(cards, output_dir=args.output_dir)
    else:
        out = evaluate_evidence_cards(cards)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("total", 0) == len(cards) else 2


if __name__ == "__main__":
    raise SystemExit(main())
