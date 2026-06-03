"""PGG Archon ECC compatibility gate.

Read-only error/cost/constraint check inspired by the historical ECC overlay.
It evaluates caller-supplied evidence and returns an explicit PASS/WATCH/BLOCKED
verdict. It never blocks Hermes execution by itself and never claims autonomous
self-healing.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping

SCHEMA = "PGGArchonECC/v2"
DEFAULT_WEIGHTS = {
    "hallucination": 30.0,
    "security": 25.0,
    "unverified_completion": 20.0,
    "missing_evidence": 15.0,
    "cost_or_latency": 5.0,
    "governance_debt": 5.0,
}


@dataclass(frozen=True)
class ECCFinding:
    name: str
    severity: float
    weight: float
    penalty: float
    detail: str


def _severity(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def evaluate_ecc(signals: Mapping[str, Any] | None = None, weights: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Evaluate defect deduction signals in a read-only, bounded way."""
    src = dict(signals or {})
    w = {**DEFAULT_WEIGHTS, **dict(weights or {})}
    findings: list[ECCFinding] = []
    for name, weight in w.items():
        raw = src.get(name, 0.0)
        if isinstance(raw, Mapping):
            sev = _severity(raw.get("severity", raw.get("score", 0.0)))
            detail = str(raw.get("detail") or raw.get("evidence") or "")[:500]
        else:
            sev = _severity(raw)
            detail = "caller_supplied_numeric_signal" if sev else "not_reported"
        findings.append(ECCFinding(name=name, severity=sev, weight=float(weight), penalty=round(sev * float(weight), 4), detail=detail))
    total_penalty = round(sum(f.penalty for f in findings), 4)
    score = round(max(0.0, 100.0 - total_penalty), 2)
    critical = [f.name for f in findings if f.severity >= 0.8 and f.weight >= 20]
    status = "BLOCKED" if critical or score < 60 else ("WATCH" if score < 85 or total_penalty > 0 else "PASS")
    payload = {
        "score": score,
        "total_penalty": total_penalty,
        "critical_findings": critical,
        "findings": [asdict(f) for f in findings],
    }
    return {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        **payload,
        "evidence_hash": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "side_effects": "read_only_ecc_evaluation",
        "boundary": "Evidence gate only; does not prove correctness, does not auto-repair, and is not an external benchmark.",
    }


def main() -> None:  # pragma: no cover
    print(json.dumps(evaluate_ecc(), ensure_ascii=False, indent=2))


__all__ = ["SCHEMA", "DEFAULT_WEIGHTS", "ECCFinding", "evaluate_ecc"]


if __name__ == "__main__":
    main()
