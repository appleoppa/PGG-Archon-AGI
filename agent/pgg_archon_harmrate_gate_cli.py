#!/usr/bin/env python3
"""CLI for PGG internal HarmRate gate."""
from __future__ import annotations

import argparse
import json

from agent.pgg_archon_harmrate_gate import compute_harmrate, write_harmrate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute PGG internal HarmRate decision; not APEX-MOSS verified.")
    parser.add_argument("task_json", help="JSON file containing task risk inputs")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    task = json.load(open(args.task_json, encoding="utf-8"))
    if not isinstance(task, dict):
        raise SystemExit("task_json must contain an object")
    out = compute_harmrate(task)
    if args.output_dir:
        out["output_path"] = write_harmrate_report(out, args.output_dir)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("decision") in {"ALLOW", "WATCH"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
