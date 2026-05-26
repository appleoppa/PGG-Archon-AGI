"""APEX RuntimeOS three-sequence state machine.

This module turns the historical APEX execution orders into a deterministic,
read-only gate.  It validates evidence shape only; it does not execute tasks,
write files, mutate memory, or advance cron cycles.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Sequence

SEQUENCE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "21354": {
        "name": "audit_error_first",
        "label_cn": "审错优先",
        "steps": ["context", "audit", "countercheck", "repair", "verify"],
        "purpose": "先识别错误前提和证据缺口，再修复和验证。",
    },
    "12534": {
        "name": "fusion_solidify",
        "label_cn": "融合固化",
        "steps": ["context", "plan", "absorb", "verify", "solidify"],
        "purpose": "先明确目标并融合来源，再验证和固化。",
    },
    "14325": {
        "name": "plan_counterevidence",
        "label_cn": "规划反证",
        "steps": ["context", "plan", "countercheck", "audit", "solidify"],
        "purpose": "先规划路径，再用反证和审计校正。",
    },
}

REQUIRED_SEQUENCE_ORDER = ("21354", "12534", "14325")
REQUIRED_ROUNDS_PER_CYCLE = 5
REQUIRED_LOOPS_PER_ROUND = 2


class SequenceValidationError(ValueError):
    """Raised when a single sequence evidence item is malformed."""


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be a mapping")
    return value


def _as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def normalize_sequence_code(code: Any) -> str:
    text = str(code or "").strip()
    if text not in SEQUENCE_DEFINITIONS:
        raise SequenceValidationError(f"unknown APEX sequence: {text or '<empty>'}")
    return text


def build_sequence_gate_report(
    records: Sequence[Mapping[str, Any]] | None = None,
    *,
    required_sequences: Iterable[str] = REQUIRED_SEQUENCE_ORDER,
) -> Dict[str, Any]:
    """Validate a flat list of APEX sequence evidence records.

    Expected record shape is intentionally small and redaction-safe::

        {"sequence": "21354", "evidence": true, "score": 0.8, "shortcoming": "..."}

    Only aggregate flags are returned.  Raw evidence text is not copied into the
    report to avoid leaking prompts, paths, or credentials.
    """
    items = list(records or [])
    required = tuple(normalize_sequence_code(code) for code in required_sequences)
    seen: Dict[str, Dict[str, Any]] = {}
    issues: list[Dict[str, Any]] = []

    for idx, raw in enumerate(items):
        try:
            item = _require_mapping(raw, field=f"records[{idx}]")
            code = normalize_sequence_code(item.get("sequence"))
        except Exception as exc:
            issues.append({"code": "malformed_record", "index": idx, "message": str(exc)})
            continue
        if code in seen:
            issues.append({"code": "duplicate_sequence", "sequence": code, "index": idx})
        score = item.get("score")
        score_ok = isinstance(score, (int, float)) and 0.0 <= float(score) <= 1.0
        has_evidence = _as_bool(item.get("evidence")) or _as_bool(item.get("evidence_exists"))
        has_shortcoming = bool(str(item.get("shortcoming") or item.get("shortcoming_source") or "").strip())
        has_output = _as_bool(item.get("output")) or _as_bool(item.get("output_exists")) or score_ok
        seen[code] = {
            "sequence": code,
            "label_cn": SEQUENCE_DEFINITIONS[code]["label_cn"],
            "score_ok": score_ok,
            "has_evidence": has_evidence,
            "has_output": has_output,
            "has_shortcoming": has_shortcoming,
        }
        if not has_evidence:
            issues.append({"code": "missing_evidence", "sequence": code})
        if not has_output:
            issues.append({"code": "missing_output", "sequence": code})
        if not has_shortcoming:
            issues.append({"code": "missing_shortcoming", "sequence": code})

    missing_sequences = [code for code in required if code not in seen]
    for code in missing_sequences:
        issues.append({"code": "missing_sequence", "sequence": code})

    observed_order = [code for code in REQUIRED_SEQUENCE_ORDER if code in seen]
    complete = not issues and tuple(observed_order) == required
    status = "PASS" if complete else ("WARN" if seen else "BLOCK")
    return {
        "schema": "ApexRuntimeOSSequenceGate/v1",
        "status": status,
        "required_order": list(required),
        "observed_order": observed_order,
        "complete": complete,
        "sequence_count": len(seen),
        "missing_sequences": missing_sequences,
        "issues": issues,
        "sequences": [seen[code] for code in REQUIRED_SEQUENCE_ORDER if code in seen],
        "definitions": SEQUENCE_DEFINITIONS,
        "side_effects": "read_only_report",
    }


def build_cycle_state_report(cycle: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Validate a historical cron-cycle evidence envelope.

    Shape accepted by this helper is aggregate and minimal::

        {"rounds": [{"round": 1, "loops": [{"sequences": [...]}, ...]}, ...]}
    """
    source = _require_mapping(cycle or {}, field="cycle")
    raw_rounds = source.get("rounds")
    rounds: list[Any] = raw_rounds if isinstance(raw_rounds, list) else []
    issues: list[Dict[str, Any]] = []
    round_reports = []
    if len(rounds) != REQUIRED_ROUNDS_PER_CYCLE:
        issues.append({"code": "round_count_mismatch", "expected": REQUIRED_ROUNDS_PER_CYCLE, "actual": len(rounds)})

    for ridx, raw_round in enumerate(rounds):
        if not isinstance(raw_round, Mapping):
            issues.append({"code": "malformed_round", "round_index": ridx})
            continue
        raw_loops = raw_round.get("loops")
        loops: list[Any] = raw_loops if isinstance(raw_loops, list) else []
        if len(loops) != REQUIRED_LOOPS_PER_ROUND:
            issues.append({"code": "loop_count_mismatch", "round_index": ridx, "expected": REQUIRED_LOOPS_PER_ROUND, "actual": len(loops)})
        loop_reports = []
        for lidx, raw_loop in enumerate(loops):
            if not isinstance(raw_loop, Mapping):
                issues.append({"code": "malformed_loop", "round_index": ridx, "loop_index": lidx})
                continue
            sequence_records = []
            raw_sequences = raw_loop.get("sequences")
            sequences: list[Any] = raw_sequences if isinstance(raw_sequences, list) else []
            for seq in sequences:
                if isinstance(seq, Mapping):
                    sequence_records.append(seq)
                else:
                    sequence_records.append({"sequence": seq, "evidence": True, "output": True, "shortcoming": "sequence listed"})
            seq_report = build_sequence_gate_report(sequence_records)
            if seq_report["status"] != "PASS":
                issues.append({"code": "sequence_gate_failed", "round_index": ridx, "loop_index": lidx, "status": seq_report["status"]})
            loop_reports.append({
                "loop_index": lidx,
                "status": seq_report["status"],
                "observed_order": seq_report["observed_order"],
                "missing_sequences": seq_report["missing_sequences"],
            })
        round_reports.append({"round_index": ridx, "loop_count": len(loops), "loops": loop_reports})

    status = "PASS" if not issues else ("WARN" if rounds else "BLOCK")
    return {
        "schema": "ApexRuntimeOSCycleState/v1",
        "status": status,
        "required_rounds": REQUIRED_ROUNDS_PER_CYCLE,
        "required_loops_per_round": REQUIRED_LOOPS_PER_ROUND,
        "required_sequences": list(REQUIRED_SEQUENCE_ORDER),
        "round_count": len(rounds),
        "issues": issues,
        "rounds": round_reports,
        "side_effects": "read_only_report",
    }


def build_sequence_gate_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose current RuntimeOS sequence readiness without claiming execution.

    Existing autonomy summaries do not yet contain per-sequence evidence.  The
    correct default is therefore a visible BLOCK/WARN gate, not a fake PASS.
    """
    return build_sequence_gate_report([])


__all__ = [
    "REQUIRED_LOOPS_PER_ROUND",
    "REQUIRED_ROUNDS_PER_CYCLE",
    "REQUIRED_SEQUENCE_ORDER",
    "SEQUENCE_DEFINITIONS",
    "SequenceValidationError",
    "build_cycle_state_report",
    "build_sequence_gate_from_runtimeos_status",
    "build_sequence_gate_report",
    "normalize_sequence_code",
]
