"""APEX triple-sequence loop runner for PGG Archon.

Runs the three APEX execution orders (21354, 12534, 14325) as deterministic,
read-only defect-reduction simulations over the EVM gate. This converts one-off
self-diagnosis scripts into a reusable, testable module.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any, Mapping

from agent.apex_runtimeos_evm_gate import DEFECT_DESCRIPTIONS, build_evm_gate_report, normalize_defects

DEFAULT_REPORT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/apex-sequence-loops")
SEQUENCES: dict[str, tuple[tuple[str, float], ...]] = {
    "21354_审错优先": (("Err", -0.025), ("Log", -0.015), ("Clw", -0.010), ("Agt", -0.005), ("Pan", -0.005)),
    "12534_融合固化": (("Mem", -0.015), ("Pan", -0.020), ("Log", -0.015), ("Agt", -0.010), ("Err", -0.005)),
    "14325_规划反证": (("Agt", -0.020), ("Net", -0.015), ("Run", -0.010), ("Err", -0.010), ("Res", -0.005)),
}
DEFAULT_PRESSURE_REBOUNDS = {"Err": 0.006, "Agt": 0.005, "Pan": 0.004, "Net": 0.004, "Res": 0.003}
DEFAULT_BASE_DEFECTS = {"Tok": 0.10, "Clw": 0.13, "Agt": 0.22, "Pan": 0.20, "Prm": 0.10, "Soul": 0.05, "Run": 0.12, "Net": 0.18, "Err": 0.24, "Mem": 0.12, "Res": 0.20, "Log": 0.18}


def _top_residuals(defects: Mapping[str, float], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"code": code, "score": score, "meaning": DEFECT_DESCRIPTIONS[code]}
        for code, score in sorted(defects.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    ]


def run_apex_triple_sequence_loops(
    base_defects: Mapping[str, Any] | None = None,
    *,
    iterations_per_sequence: int = 5,
    pressure_rebounds: Mapping[str, float] | None = None,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    base = normalize_defects(base_defects or DEFAULT_BASE_DEFECTS)
    rebounds = dict(DEFAULT_PRESSURE_REBOUNDS)
    if pressure_rebounds:
        rebounds.update({str(k): float(v) for k, v in pressure_rebounds.items()})
    runs: list[dict[str, Any]] = []
    for sequence_name, steps in SEQUENCES.items():
        cur = dict(base)
        for iteration in range(1, iterations_per_sequence + 1):
            before = dict(cur)
            for code, delta in steps:
                cur[code] = max(0.02, min(1.0, cur[code] + delta))
            for code, delta in rebounds.items():
                if code in cur:
                    cur[code] = max(0.02, min(1.0, cur[code] + delta))
            evm = build_evm_gate_report(before, after_defects=cur, trace_written=True, memory_marked_temporary=True, validation_passed=True)
            runs.append({
                "sequence": sequence_name,
                "iteration": iteration,
                "evm_status": evm["status"],
                "evm_value": evm["evm_value"],
                "governance_reduction": evm["governance_reduction"],
                "top_residuals": _top_residuals(cur),
                "after_defects": cur.copy(),
            })
    finals = [run for run in runs if run["iteration"] == iterations_per_sequence]
    aggregate: dict[str, list[float]] = {}
    for run in finals:
        for code, value in run["after_defects"].items():
            aggregate.setdefault(code, []).append(float(value))
    bottlenecks = sorted(
        [{"code": code, "avg_final_score": round(mean(values), 3), "meaning": DEFECT_DESCRIPTIONS[code]} for code, values in aggregate.items()],
        key=lambda item: item["avg_final_score"],
        reverse=True,
    )
    report = {
        "schema": "ApexTripleSequenceLoopReport/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sequence_count": len(SEQUENCES),
        "iterations_per_sequence": iterations_per_sequence,
        "run_count": len(runs),
        "runs": runs,
        "bottlenecks": bottlenecks[:8],
        "next_unlock_candidates": [
            {"module": "open_source_alignment_ledger", "targets": ["Clw", "Err"], "risk": "low"},
            {"module": "apex_module_unlock_registry", "targets": ["Pan", "Mem"], "risk": "low"},
            {"module": "graph_replay_case_flow", "targets": ["Agt", "Pan"], "risk": "medium"},
        ],
        "side_effects": "report_write" if write_report else "read_only_report",
        "agi_completion_claim": False,
    }
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_apex_triple_sequence_loop.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


__all__ = ["DEFAULT_BASE_DEFECTS", "SEQUENCES", "run_apex_triple_sequence_loops"]
