#!/usr/bin/env python3
"""Run the PGG Archon ultimate evolution Phase 3 ARS sidecar cycle.

Designed for cron/no_agent usage.  Prints a compact one-line status so empty
stdout never hides a broken run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from agent.pgg_archon_ultimate_evolution_ars_cycle import run_phase3_cycle, run_phase4_cycle, run_phase5_cycle, run_phase6_cycle, run_phase7_cycle, run_phase8_cycle, run_phase9_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 3 ultimate evolution ARS sidecar cycle")
    parser.add_argument("--persist", action="store_true", help="Persist experiment/gene summary to PGG SQLite")
    parser.add_argument("--phase4", action="store_true", help="Run Phase 4 trend replay and dedup gate after Phase 3")
    parser.add_argument("--phase5", action="store_true", help="Run Phase 5 promotion gate fusion after Phase 4")
    parser.add_argument("--phase6", action="store_true", help="Run Phase 6 native tool status surface after Phase 5")
    parser.add_argument("--phase7", action="store_true", help="Run Phase 7 evidence-chain status after Phase 6")
    parser.add_argument("--phase8", action="store_true", help="Run Phase 8 chain integrity manifest gate after Phase 7")
    parser.add_argument("--phase9", action="store_true", help="Run Phase 9 cron/CI drift gate after Phase 8")
    parser.add_argument("--non-idempotent", action="store_true", help="Allow duplicate Phase 3 DB inserts; disabled by default")
    parser.add_argument("--json", action="store_true", help="Print JSON result instead of compact status line")
    args = parser.parse_args()
    result = run_phase3_cycle(persist=args.persist, idempotent=not args.non_idempotent)
    if args.phase4:
        result["phase4"] = run_phase4_cycle(persist=args.persist)
    if args.phase5:
        if not args.phase4:
            result["phase4"] = run_phase4_cycle(persist=args.persist)
        result["phase5"] = run_phase5_cycle(persist=args.persist)
    if args.phase6:
        if "phase4" not in result:
            result["phase4"] = run_phase4_cycle(persist=args.persist)
        if "phase5" not in result:
            result["phase5"] = run_phase5_cycle(persist=args.persist)
        result["phase6"] = run_phase6_cycle(persist=args.persist)
    if args.phase7:
        if "phase4" not in result:
            result["phase4"] = run_phase4_cycle(persist=args.persist)
        if "phase5" not in result:
            result["phase5"] = run_phase5_cycle(persist=args.persist)
        if "phase6" not in result:
            result["phase6"] = run_phase6_cycle(persist=args.persist)
        result["phase7"] = run_phase7_cycle(persist=args.persist)
    if args.phase8:
        if "phase4" not in result:
            result["phase4"] = run_phase4_cycle(persist=args.persist)
        if "phase5" not in result:
            result["phase5"] = run_phase5_cycle(persist=args.persist)
        if "phase6" not in result:
            result["phase6"] = run_phase6_cycle(persist=args.persist)
        if "phase7" not in result:
            result["phase7"] = run_phase7_cycle(persist=args.persist)
        result["phase8"] = run_phase8_cycle(persist=args.persist)
    if args.phase9:
        if "phase4" not in result:
            result["phase4"] = run_phase4_cycle(persist=args.persist)
        if "phase5" not in result:
            result["phase5"] = run_phase5_cycle(persist=args.persist)
        if "phase6" not in result:
            result["phase6"] = run_phase6_cycle(persist=args.persist)
        if "phase7" not in result:
            result["phase7"] = run_phase7_cycle(persist=args.persist)
        if "phase8" not in result:
            result["phase8"] = run_phase8_cycle(persist=args.persist)
        result["phase9"] = run_phase9_cycle(persist=args.persist)
    payload = result["payload"]
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        db = result.get("pgg_db") or {}
        suffix = ""
        if args.phase4:
            suffix += (
                " "
                f"phase4_report={result['phase4']['paths']['json']} "
                f"phase4_gene_id={result['phase4'].get('pgg_db', {}).get('gene_id')}"
            )
        if args.phase5:
            suffix += (
                " "
                f"phase5_status={result['phase5']['gate'].get('status')} "
                f"phase5_report={result['phase5']['paths']['json']} "
                f"phase5_gene_id={result['phase5'].get('pgg_db', {}).get('gene_id')}"
            )
        if args.phase6:
            suffix += (
                " "
                f"phase6_status={result['phase6']['surface'].get('status')} "
                f"phase6_report={result['phase6']['paths']['json']} "
                f"phase6_gene_id={result['phase6'].get('pgg_db', {}).get('gene_id')}"
            )
        if args.phase7 or args.phase8 or args.phase9:
            suffix += (
                " "
                f"phase7_status={result['phase7']['chain'].get('status')} "
                f"phase7_report={result['phase7']['paths']['json']} "
                f"phase7_gene_id={result['phase7'].get('pgg_db', {}).get('gene_id')}"
            )
        if args.phase8 or args.phase9:
            suffix += (
                " "
                f"phase8_status={result['phase8']['gate'].get('status')} "
                f"phase8_manifest_hash={result['phase8']['gate'].get('manifest_hash')} "
                f"phase8_report={result['phase8']['paths']['json']} "
                f"phase8_gene_id={result['phase8'].get('pgg_db', {}).get('gene_id')}"
            )
        if args.phase9:
            suffix += (
                " "
                f"phase9_status={result['phase9']['gate'].get('status')} "
                f"phase9_gate_hash={result['phase9']['gate'].get('gate_hash')} "
                f"phase9_report={result['phase9']['paths']['json']} "
                f"phase9_gene_id={result['phase9'].get('pgg_db', {}).get('gene_id')}"
            )
        print(
            "PGG ultimate evolution Phase3 ARS complete: "
            f"status={payload.get('status')} score={payload.get('score')} "
            f"decision={payload.get('decision')} "
            f"report={result['paths']['json']} "
            f"gene_id={db.get('gene_id')} deduped={db.get('deduped')}"
            + suffix
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
