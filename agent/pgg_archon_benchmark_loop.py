"""PGG Archon integrated benchmark loop.

This adapter connects the minimal AGI task benchmark harness to the already-built
PGG Archon foundation:

- ``agent.agi_task_benchmark`` for deterministic task scoring and failure queue.
- ``agent.pgg_archon_delta_gate`` for Delta-G/anti-hallucination signal checks.
- Rust-native ``hermes_pgg_status`` and ``hermes_pgg_ecc`` read-only surfaces.
- Rust-native ``hermes_apex_evolution`` APEX ΔE evaluation when a workspace is
  provided.

Boundary: this is an internal PGG Archon evaluation loop, not full AGI, not an
external AGI benchmark, and not legal correctness proof.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.agi_task_benchmark import (
    BenchmarkRun,
    BenchmarkTask,
    evaluate_predictions,
    write_benchmark_outputs,
)
from agent.pgg_archon_delta_gate import run_anti_hallucination


@dataclass(frozen=True)
class IntegratedBenchmarkResult:
    schema: str
    generated_at: str
    status: str
    benchmark_run: dict[str, Any]
    output_paths: dict[str, str]
    pgg_status: dict[str, Any]
    pgg_ecc: dict[str, Any]
    delta_gate: dict[str, Any]
    apex_delta_e: dict[str, Any] | None
    evolution_queue_count: int
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json_or_text(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except Exception as exc:  # noqa: BLE001 - provider/Rust surface may return unexpected text
        return {"parse_error": type(exc).__name__, "raw": text}


def _rust_status_summary(passed: int, total: int) -> dict[str, Any]:
    try:
        import hermes_pgg_status

        return _load_json_or_text(hermes_pgg_status.summarize(passed, total))
    except Exception as exc:  # noqa: BLE001 - keep loop robust and honest
        return {"schema": "HermesPGGStatusRust/v1", "status": "WATCH", "error": repr(exc)}


def _rust_ecc_summary(run: BenchmarkRun) -> dict[str, Any]:
    failure_ratio = 1.0 - (run.passed_tasks / run.total_tasks if run.total_tasks else 0.0)
    signals = {
        "missing_evidence": failure_ratio,
        "unverified_completion": failure_ratio,
        "governance_debt": 0.0 if run.status == "PASS" else min(1.0, failure_ratio),
    }
    try:
        import hermes_pgg_ecc

        report = _load_json_or_text(hermes_pgg_ecc.evaluate(json.dumps(signals)))
        report["signals"] = signals
        return report
    except Exception as exc:  # noqa: BLE001
        return {"schema": "HermesPGGEccRust/v1", "status": "WATCH", "signals": signals, "error": repr(exc)}


def _delta_gate_summary(run: BenchmarkRun) -> dict[str, Any]:
    failed = [score for score in run.task_scores if not score.passed]
    text = "\n".join(f"{s.task_id}: expected={s.expected} prediction={s.prediction}" for s in failed)
    if not text:
        text = "All benchmark tasks passed. This is not full AGI proof."
    try:
        gate = run_anti_hallucination(text)
        return {
            "schema": "PGGDeltaGateBenchmarkSignal/v1",
            "state": gate.state,
            "delta_g_total": round(float(gate.delta_g.total), 6),
            "repairs_needed": list(gate.repairs_needed),
            "confidence": round(float(gate.confidence), 6),
            "boundary": "Delta-G heuristic over benchmark failure text; not legal correctness proof.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"schema": "PGGDeltaGateBenchmarkSignal/v1", "state": "WATCH", "error": repr(exc)}


def _apex_eval(workspace: str | Path | None, output_dir: Path) -> dict[str, Any] | None:
    if workspace is None:
        return None
    try:
        import hermes_apex_evolution

        out = output_dir / "apex_delta_e.json"
        hermes_apex_evolution.py_evaluate(str(Path(workspace).expanduser()), str(out))
        if out.exists():
            return json.loads(out.read_text(encoding="utf-8"))
        return {"status": "WATCH", "error": "apex output file missing", "output": str(out)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "WATCH", "error": repr(exc)}


def run_integrated_benchmark(
    tasks: Sequence[BenchmarkTask],
    predictions: Mapping[str, Any],
    *,
    output_dir: str | Path,
    run_id: str | None = None,
    workspace_for_apex: str | Path | None = None,
) -> IntegratedBenchmarkResult:
    """Run benchmark scoring plus PGG Archon governance surfaces."""
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    run = evaluate_predictions(tasks, predictions, run_id=run_id)
    paths = write_benchmark_outputs(run, output_dir=out)
    pgg_status = _rust_status_summary(run.passed_tasks, run.total_tasks)
    pgg_ecc = _rust_ecc_summary(run)
    delta_gate = _delta_gate_summary(run)
    apex_delta_e = _apex_eval(workspace_for_apex, out)

    queue_path = Path(paths["evolution_queue"])
    queue_count = 0
    if queue_path.exists():
        queue_count = sum(1 for line in queue_path.read_text(encoding="utf-8").splitlines() if line.strip())

    status = "PASS" if run.status == "PASS" and pgg_ecc.get("status") == "PASS" else "WATCH"
    result = IntegratedBenchmarkResult(
        schema="PGGArchonIntegratedBenchmarkLoop/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        benchmark_run=run.to_json_dict(),
        output_paths=paths,
        pgg_status=pgg_status,
        pgg_ecc=pgg_ecc,
        delta_gate=delta_gate,
        apex_delta_e=apex_delta_e,
        evolution_queue_count=queue_count,
        boundary=(
            "Internal PGG Archon benchmark loop using existing Rust/ECC/Delta/APEX surfaces; "
            "not full AGI, not external AGI benchmark, not legal correctness proof."
        ),
    )
    integrated_path = out / f"{run.run_id}.integrated.json"
    integrated_path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    result.output_paths["integrated"] = str(integrated_path)
    # Re-write after adding integrated path to the returned object.
    integrated_path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
