"""PGG Archon memory/trace scorer.
Boundary: pure calculation from supplied metrics; no I/O, no LLM calls, no persistence.
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

    def score(memory_metrics: dict[str, Any], trace_metrics: dict[str, Any]) -> dict[str, Any]:
        raw = _native_mod.score(json.dumps(memory_metrics), json.dumps(trace_metrics))
        return json.loads(raw)

else:

    def _avg(
        metrics: dict[str, Any],
        keys: list[str],
        warnings: list[str],
        prefix: str,
    ) -> float | None:
        vals = []
        for k in keys:
            if k in metrics:
                try:
                    v = float(metrics[k])
                    vals.append(max(0.0, min(1.0, v)))
                except (TypeError, ValueError):
                    warnings.append(f"{prefix}.{k} not numeric")
        return sum(vals) / len(vals) if vals else None

    def score(memory_metrics: dict[str, Any], trace_metrics: dict[str, Any]) -> dict[str, Any]:
        """Return status/sigma_memory/tau_trace/combined/warnings from real inputs."""
        warnings: list[str] = []
        if not isinstance(memory_metrics, dict) or not isinstance(trace_metrics, dict):
            return {
                "status": "BLOCKED",
                "sigma_memory": 0.0,
                "tau_trace": 0.0,
                "combined": 0.0,
                "warnings": ["metrics must be dicts"],
            }
        sigma = _avg(memory_metrics, ["learn", "search", "multimodal", "profile", "retention", "diversity"], warnings, "memory")
        tau = _avg(trace_metrics, ["decision", "reason", "result", "evidence"], warnings, "trace")
        if sigma is None:
            warnings.append("no valid memory metrics")
            sigma = 0.0
        if tau is None:
            warnings.append("no valid trace metrics")
            tau = 0.0
        combined = round(sigma * 0.6 + tau * 0.4, 6)
        if not memory_metrics or not trace_metrics:
            status = "BLOCKED"
        elif combined >= 0.7:
            status = "PASS"
        elif combined >= 0.4:
            status = "WATCH"
        else:
            status = "BLOCKED"
        return {
            "status": status,
            "sigma_memory": round(sigma, 6),
            "tau_trace": round(tau, 6),
            "combined": combined,
            "warnings": warnings,
        }


__all__ = ["score"]