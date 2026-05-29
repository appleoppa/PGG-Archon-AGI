"""APEX RuntimeOS EVM twelve-defect gate.

This module extracts the safe, deterministic subset of the historical EVM
Entropy-Vibe-Mathing formula into Hermes RuntimeOS.  It is intentionally
read-only: it calculates a defect gate report and never mutates runtime state,
files, memory, or gene databases.

EVM here means the APEX evolution defect gate, not blockchain EVM.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Mapping

DEFECT_CODES = (
    "Tok",  # token/context loss
    "Clw",  # tool/claw execution failure
    "Agt",  # agent concurrency conflict
    "Pan",  # board/scheduler visibility failure
    "Prm",  # prompt initialization defect
    "Soul",  # core self-description drift
    "Run",  # runtime crash/delay
    "Net",  # network/API disconnection
    "Err",  # hallucination/error
    "Mem",  # memory loss/cross-talk
    "Res",  # resource overload
    "Log",  # missing trace/log
)

DEFECT_DESCRIPTIONS = {
    "Tok": "token/context loss",
    "Clw": "tool/claw execution failure",
    "Agt": "agent concurrency conflict",
    "Pan": "board/scheduler visibility failure",
    "Prm": "prompt initialization defect",
    "Soul": "core self-description drift",
    "Run": "runtime crash/delay",
    "Net": "network/API disconnection",
    "Err": "hallucination/error",
    "Mem": "memory loss/cross-talk",
    "Res": "resource overload",
    "Log": "missing trace/log",
}

# Historical EVM defaults from z-dashen/evm/CoreFormula/EVM_FORMULA.py.
MODERN_FACTORS = {
    "E": 0.92,
    "V": 0.88,
    "M": 0.95,
    "A": 1.00,
    "Base": 1.00,
}

ANCIENT_FACTORS = {
    "TaoTeChing": 1.00,
    "IChing": 1.00,
    "HuangDi": 1.00,
    "HeTuLuoShu": 1.00,
    "GanZhi": 1.00,
    "WuXing": 1.00,
    "Bagua": 1.00,
}

EVM_PASS_THRESHOLD = 0.75
EVM_WARN_THRESHOLD = 0.60


def _clamp01(value: Any, *, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be finite")
    if numeric < 0.0 or numeric > 1.0:
        raise ValueError(f"{field} must be in [0, 1]")
    return numeric


def normalize_defects(defects: Mapping[str, Any] | None) -> Dict[str, float]:
    """Return a complete twelve-defect vector with validated [0, 1] values."""
    source = defects or {}
    unknown = sorted(str(key) for key in source.keys() if str(key) not in DEFECT_CODES)
    if unknown:
        raise ValueError(f"unknown EVM defect code(s): {', '.join(unknown)}")
    return {code: _clamp01(source.get(code, 0.0), field=f"defect.{code}") for code in DEFECT_CODES}


def infer_defects_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, float]:
    """Infer a conservative defect vector from aggregate RuntimeOS status.

    The mapping is intentionally small and explainable.  It uses only aggregate
    counts from RuntimeOS autonomy status and does not inspect raw prompts,
    messages, paths, credentials, or trace bodies.
    """
    defects = {code: 0.0 for code in DEFECT_CODES}
    cron = status.get("cron_dryrun") if isinstance(status.get("cron_dryrun"), Mapping) else {}
    health = status.get("health_report") if isinstance(status.get("health_report"), Mapping) else {}
    bad_lines = int(cron.get("bad_lines") or 0) if isinstance(cron, Mapping) else 0
    pending_rollbacks = int(status.get("pending_rollbacks") or 0)
    stable_ready = int(status.get("stable_ready_count") or 0)
    alert_count = int(health.get("alert_count") or 0) if isinstance(health, Mapping) else 0

    if bad_lines:
        defects["Log"] = min(1.0, bad_lines / 10.0)
        defects["Run"] = max(defects["Run"], min(1.0, bad_lines / 20.0))
    if pending_rollbacks:
        defects["Err"] = min(1.0, pending_rollbacks / 10.0)
        defects["Mem"] = max(defects["Mem"], min(1.0, pending_rollbacks / 20.0))
    if stable_ready:
        defects["Mem"] = max(defects["Mem"], min(1.0, stable_ready / 20.0))
    if alert_count:
        defects["Res"] = min(1.0, alert_count / 10.0)
    return defects


def _product(values: Mapping[str, float]) -> float:
    result = 1.0
    for value in values.values():
        result *= _clamp01(value, field="factor")
    return result


def build_evm_gate_report(
    defects: Mapping[str, Any] | None = None,
    *,
    after_defects: Mapping[str, Any] | None = None,
    trace_written: bool = False,
    memory_persisted: bool = False,
    memory_marked_temporary: bool = False,
    validation_passed: bool = False,
) -> Dict[str, Any]:
    """Build a deterministic EVM gate report.

    If ``after_defects`` is omitted, the current defect vector is evaluated as
    the residual vector.  If provided, reduction is computed from before to after.
    """
    before = normalize_defects(defects)
    after = normalize_defects(after_defects) if after_defects is not None else dict(before)
    modern_factor = _product(MODERN_FACTORS)
    ancient_factor = _product(ANCIENT_FACTORS)
    raw_defect_rate = sum(before.values()) / len(DEFECT_CODES)
    governed_defect_rate = sum(after.values()) / len(DEFECT_CODES)
    reduction = max(0.0, raw_defect_rate - governed_defect_rate)
    evm_value = max(0.0, min(1.0, modern_factor * ancient_factor * (1.0 - governed_defect_rate)))

    missing = []
    if not trace_written:
        missing.append("trace_written")
    if not validation_passed:
        missing.append("validation_passed")
    memory_evidence_present = bool(memory_persisted) or bool(memory_marked_temporary)
    if not memory_evidence_present:
        missing.append("memory_persisted_or_marked_temporary")

    if evm_value >= EVM_PASS_THRESHOLD and trace_written and validation_passed and memory_evidence_present:
        gate_status = "PASS"
    elif evm_value < EVM_WARN_THRESHOLD:
        gate_status = "BLOCK"
    else:
        gate_status = "WARN"

    return {
        "schema": "ApexRuntimeOSEVMGate/v1",
        "status": gate_status,
        "evm_value": round(evm_value, 6),
        "thresholds": {"pass": EVM_PASS_THRESHOLD, "warn": EVM_WARN_THRESHOLD},
        "modern_factor": round(modern_factor, 6),
        "ancient_factor": round(ancient_factor, 6),
        "raw_defect_rate": round(raw_defect_rate, 6),
        "governed_defect_rate": round(governed_defect_rate, 6),
        "governance_reduction": round(reduction, 6),
        "before_defects": before,
        "after_defects": after,
        "defect_descriptions": DEFECT_DESCRIPTIONS,
        "trace_written": bool(trace_written),
        "memory_persisted": bool(memory_persisted),
        "memory_marked_temporary": bool(memory_marked_temporary),
        "memory_evidence_present": memory_evidence_present,
        "validation_passed": bool(validation_passed),
        "missing_completion_evidence": missing,
        "side_effects": "read_only_report",
        "boundary": "EVM means APEX RuntimeOS defect gate, not blockchain EVM.",
    }


def build_evm_gate_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    defects = infer_defects_from_runtimeos_status(status)
    rollback_events = status.get("rollback_events") if isinstance(status.get("rollback_events"), Mapping) else {}
    rollback_done = 0
    if isinstance(rollback_events, Mapping):
        raw_status = rollback_events.get("status") if isinstance(rollback_events.get("status"), Mapping) else {}
        rollback_done = int(raw_status.get("done") or 0) if isinstance(raw_status, Mapping) else 0
    pending_rollbacks = int(status.get("pending_rollbacks") or 0)
    memory_marked_temporary = rollback_done > 0 and pending_rollbacks == 0
    # Summary generation itself is a trace and validation signal.  Memory is not
    # called persisted unless the durable store remains in use; a completed
    # rollback can only count as a temporary/rolled-back evidence marker.
    return build_evm_gate_report(
        defects,
        trace_written=True,
        validation_passed=True,
        memory_persisted=False,
        memory_marked_temporary=memory_marked_temporary,
    )


__all__ = [
    "DEFECT_CODES",
    "DEFECT_DESCRIPTIONS",
    "build_evm_gate_report",
    "build_evm_gate_from_runtimeos_status",
    "infer_defects_from_runtimeos_status",
    "normalize_defects",
]
