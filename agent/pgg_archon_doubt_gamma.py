"""PGG Archon doubt-gamma classifier.
Boundary: pure text/risk classification; no side effects, no approval, no provider calls.
"""
from __future__ import annotations

from typing import Any

try:
    import hermes_pgg_archon_utils as _native_mod  # type: ignore[import-untyped]

    _NATIVE = True
except ImportError:
    _NATIVE = False

import json


if _NATIVE:

    def classify_decision(decision: Any, crosses_boundary: bool = False) -> dict[str, Any]:
        text = decision if isinstance(decision, str) else str(decision)
        raw = _native_mod.classify_decision(text, crosses_boundary)
        return json.loads(raw)

else:

    def classify_decision(decision: Any, crosses_boundary: bool = False) -> dict[str, Any]:
        text = decision if isinstance(decision, str) else str(decision)
        lower = text.lower()
        risk_factors = []
        score = 0.0
        for kw, w in {
            "delete": 0.2,
            "drop": 0.2,
            "destroy": 0.25,
            "production": 0.2,
            "deploy": 0.15,
            "override": 0.15,
            "force": 0.15,
            "credential": 0.25,
            "secret": 0.25,
            "security": 0.2,
        }.items():
            if kw in lower:
                risk_factors.append(kw)
                score += w
        if crosses_boundary:
            risk_factors.append("crosses_boundary")
            score += 0.4
        if not text.strip():
            risk_factors.append("empty_decision")
            score += 0.5
        gamma = round(min(1.0, max(0.0, score)), 4)
        if gamma >= 0.7:
            level = "high"
        elif gamma >= 0.4:
            level = "medium"
        elif gamma > 0:
            level = "low"
        else:
            level = "none"
        return {
            "requires_review": bool(crosses_boundary or gamma >= 0.4),
            "doubt_level": level,
            "gamma": gamma,
            "risk_factors": risk_factors,
        }


__all__ = ["classify_decision"]