"""Batch proof-packet metabolism loop.

Orchestrates the already-bounded gates:
Phase2 Promotion Authority Matrix -> Phase3 Proof Packet Completion ->
Phase4 Controlled GeneDB Mutation -> repair backlog/net-gain report.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

SCHEMA = "PGGBatchProofMetabolismLoop/v0.2"
BOUNDARY = "BATCH_LOOP_MAX10_BACKUP_DIFF_ROLLBACK_RUST_MUTATION_PREFERRED_NO_LEGAL_SECURITY_AUTO_PROMOTION"
HOME = Path.home()
BIN = HOME / ".hermes/bin"
DEFAULT_ROOT = HOME / ".hermes/workspace/pgg-archon-governance/metabolic-evolution-phase5-batch-loop"
DEFAULT_GENEDB = HOME / ".hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"
RUST_RUNNER = BIN / "pgg-batch-proof-metabolism-runner-rs"

Runner = Callable[[list[str], int], dict[str, Any]]


def _now_tag() -> str:
    return time.strftime("%Y%m%dT%H%M%S%z")


def _run_cmd(cmd: list[str], timeout: int = 300) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return {"exit_code": proc.returncode, "output": proc.stdout}


def _parse_json_output(result: dict[str, Any], phase: str) -> dict[str, Any]:
    if result.get("exit_code") != 0:
        raise RuntimeError(f"{phase} failed: {result.get('output', '')[-4000:]}")
    output = result.get("output", "").strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{phase} did not return JSON: {output[-4000:]}") from exc


def _write_repair_backlog(completion_results: Path, outdir: Path) -> dict[str, Any]:
    if not completion_results.exists():
        backlog: list[dict[str, Any]] = []
    else:
        rows = json.loads(completion_results.read_text(encoding="utf-8"))
        backlog = [
            {
                "task_id": r.get("task_id"),
                "capability_id": r.get("capability_id"),
                "verdict": r.get("verdict"),
                "source_file": r.get("source_file"),
                "missing_evidence": r.get("missing_evidence", []),
                "action": "repair_source_ref_or_add_test" if r.get("verdict") in {"BLOCKED_SOURCE_MISSING", "BLOCKED_TEST_MISSING"} else "human_review_or_more_evidence",
            }
            for r in rows
            if str(r.get("verdict", "")).startswith("BLOCKED") or str(r.get("verdict", "")).startswith("WATCH")
        ]
    path = outdir / "repair_backlog.json"
    path.write_text(json.dumps(backlog, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"repair_backlog_path": str(path), "repair_backlog_count": len(backlog)}


def run_batch_metabolism_loop(
    outdir: str | Path | None = None,
    *,
    limit: int = 10,
    execute: bool = False,
    prefer_rust_mutation: bool = True,
    db_path: str | Path = DEFAULT_GENEDB,
    runner: Runner = _run_cmd,
) -> dict[str, Any]:
    """Run one bounded batch metabolism loop."""
    if limit > 10:
        raise ValueError("limit must be <= 10 for bounded metabolism loop")
    root = Path(outdir) if outdir else DEFAULT_ROOT / _now_tag()
    root.mkdir(parents=True, exist_ok=True)
    phase2_dir = root / "phase2"
    phase3_dir = root / "phase3"
    phase4_dir = root / "phase4_execute" if execute else root / "phase4_dryrun"

    phase2_cmd = [str(BIN / "pgg-promotion-authority-matrix"), "--limit-review", str(limit), "--outdir", str(phase2_dir)]
    phase2 = _parse_json_output(runner(phase2_cmd, 300), "phase2")
    phase2_rundir = Path(phase2["rundir"])
    queue = phase2_rundir / "proof_packet_queue.json"

    phase3_cmd = [str(BIN / "pgg-proof-packet-completion"), "--queue", str(queue), "--outdir", str(phase3_dir), "--limit", str(limit)]
    phase3 = _parse_json_output(runner(phase3_cmd, 300), "phase3")

    proposal_path = phase3_dir / "controlled_promotion_proposal.json"
    results_path = phase3_dir / "completion_results.json"
    use_rust_mutation = prefer_rust_mutation and RUST_RUNNER.exists()
    if use_rust_mutation:
        phase4_cmd = [
            str(RUST_RUNNER),
            "--rust-controlled-mutation", str(Path(db_path)),
            str(proposal_path),
            str(results_path),
            "--outdir", str(phase4_dir),
        ]
    else:
        phase4_cmd = [
            str(BIN / "pgg-controlled-genedb-mutation"),
            "--proposal", str(proposal_path),
            "--results", str(results_path),
            "--outdir", str(phase4_dir),
        ]
    if execute:
        phase4_cmd.append("--execute")
    phase4 = _parse_json_output(runner(phase4_cmd, 300), "phase4")

    repair = _write_repair_backlog(phase3_dir / "completion_results.json", root)
    net_gain = {
        "promoted": int(phase4.get("promoted_count", 0) or 0),
        "blocked_source_missing": int(phase4.get("source_missing_marked_count", 0) or 0),
        "queue_reduced_estimate": int(phase4.get("promoted_count", 0) or 0) + int(phase4.get("source_missing_marked_count", 0) or 0),
    }
    summary = {
        "schema": SCHEMA,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "outdir": str(root),
        "limit": limit,
        "execute": execute,
        "db_mutation": bool(phase4.get("db_mutation")),
        "mutation_backend": "rust" if use_rust_mutation else "python",
        "db_path": str(Path(db_path)),
        "backup_path": phase4.get("backup_path"),
        "phase2": phase2,
        "phase3": phase3,
        "phase4": phase4,
        "net_gain": net_gain,
        **repair,
        "boundary": BOUNDARY,
    }
    (root / "batch_loop_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


__all__ = ["run_batch_metabolism_loop"]
