#!/usr/bin/env python3
"""Standalone CLI for PGG AgentSPEX-inspired full harness spec gate."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agent.pgg_archon_evolution_pattern_gates import agentspex_full_harness_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a PGG AgentSPEX-like full harness task spec.")
    parser.add_argument("spec_json")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    packet = json.load(open(args.spec_json, encoding="utf-8"))
    out = agentspex_full_harness_gate(packet)
    if args.output_dir:
        out_dir = Path(args.output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{int(time.time())}_agentspex_full_harness_gate.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        out["output_path"] = str(path)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") in {"PASS", "WATCH"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
