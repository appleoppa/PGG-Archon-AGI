"""PGG Archon read-only debate compatibility surface.

This is a small, honest replacement for the historical multi-agent debate
overlay. It does not call LLMs or pretend autonomous agents participated. It
scores caller-supplied positions and returns a structured debate summary that
can be used as an evidence gate before real model/provider calls.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

SCHEMA = "PGGArchonDebate/v2"


@dataclass(frozen=True)
class DebatePosition:
    name: str
    stance: str
    score: float
    evidence: str
    risks: tuple[str, ...]


def _clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except Exception:
        return 0.0


def _as_risks(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(x)[:240] for x in value)
    if value:
        return (str(value)[:240],)
    return ()


def normalize_position(item: Mapping[str, Any], index: int = 0) -> DebatePosition:
    return DebatePosition(
        name=str(item.get("name") or item.get("agent") or f"position_{index}"),
        stance=str(item.get("stance") or item.get("opinion") or item.get("claim") or "WATCH"),
        score=_clamp_score(item.get("score", item.get("confidence", 0.0))),
        evidence=str(item.get("evidence") or item.get("reason") or "no_evidence_supplied")[:1000],
        risks=_as_risks(item.get("risks") or item.get("warnings")),
    )


def run_debate(positions: Sequence[Mapping[str, Any]] | None = None, objective: str = "") -> dict[str, Any]:
    """Summarize supplied positions without invoking models or mutating state."""
    raw = list(positions or [])
    normalized = [normalize_position(item, i) for i, item in enumerate(raw) if isinstance(item, Mapping)]
    if not normalized:
        normalized = [
            DebatePosition(
                name="truthfulness_gate",
                stance="WATCH",
                score=50.0,
                evidence="No debate positions supplied; cannot claim multi-agent consensus.",
                risks=("missing_positions",),
            )
        ]
    avg = sum(p.score for p in normalized) / len(normalized)
    risk_count = sum(len(p.risks) for p in normalized)
    status = "PASS" if avg >= 80 and risk_count == 0 else ("WATCH" if avg >= 50 else "BLOCKED")
    payload = {
        "objective": objective,
        "positions": [asdict(p) for p in normalized],
        "average_score": round(avg, 2),
        "risk_count": risk_count,
    }
    return {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "summary": payload,
        "consensus": status,
        "evidence_hash": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "side_effects": "read_only_summary",
        "boundary": "This module does not call LLMs or spawn agents; real multi-model participation needs separate provider/API evidence.",
    }


def main() -> None:  # pragma: no cover
    print(json.dumps(run_debate(), ensure_ascii=False, indent=2))


__all__ = ["SCHEMA", "DebatePosition", "normalize_position", "run_debate"]


if __name__ == "__main__":
    main()
