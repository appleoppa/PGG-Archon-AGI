"""PGG Archon ultimate evolution formula sidecar.

This module embeds the user-named "终极进化公式 / APEX Ultimate" into Hermes Agent as a
bounded, read-only scoring surface:

    APEX_Ultimate = Ω_A · α_ack · β_bg · ΨΛΓΞΦΥ · EVM · A · B · TDHLGWB - ΣΔ_all
    APEX_ULT = Ω_A · α_ackβ_bg · Θ_stable · EVM · Tao - ΔΣ

It deliberately does not mutate the agent loop, provider routing, memory,
skills, tools, credentials, or gene stores.  It is designed to be consumed by
native Hermes surfaces such as reports, cron jobs, skills, tools, SessionDB
summaries, and later guarded promotion gates.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

try:
    import hermes_pgg_ultimate_formula as _native_mod  # type: ignore[import-untyped]

    _NATIVE = True
except ImportError:
    _NATIVE = False

import json
import math
import time

if _NATIVE:

    def compute_evm_full(signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        return json.loads(_native_mod.compute_evm_full(json.dumps(signals or {})))

    def compute_sigma_delta(delta_signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        return json.loads(_native_mod.compute_sigma_delta(json.dumps(delta_signals or {})))

    def compute_omega_a(value: Any = None, *, apex_net: Any = None, baseline_net: Any = None) -> Dict[str, Any]:
        return json.loads(
            _native_mod.compute_omega_a(
                json.dumps(value) if value is not None else "null",
                json.dumps(apex_net) if apex_net is not None else "null",
                json.dumps(baseline_net) if baseline_net is not None else "null",
            )
        )

    def compute_theta_stable(signals: Mapping[str, Any] | None = None, *, direct_value: Any = None) -> Dict[str, Any]:
        return json.loads(
            _native_mod.compute_theta_stable(
                json.dumps(signals) if signals else "null",
                json.dumps(direct_value) if direct_value is not None else "null",
            )
        )

    def build_ultimate_evolution_formula_report(
        *,
        evm_signals: Mapping[str, Any] | None = None,
        delta_signals: Mapping[str, Any] | None = None,
        omega_a: Any = None,
        apex_net: Any = None,
        baseline_net: Any = None,
        alpha_ack: Any = 1.0,
        beta_bg: Any = 1.0,
        theta_stable_signals: Mapping[str, Any] | None = None,
        theta_stable: Any = None,
        tao_signals: Mapping[str, Any] | None = None,
        critical_threshold: float = 1.0,
    ) -> Dict[str, Any]:
        return json.loads(
            _native_mod.build_ultimate_evolution_formula_report(
                json.dumps(evm_signals) if evm_signals is not None else "null",
                json.dumps(delta_signals) if delta_signals is not None else "null",
                json.dumps(omega_a) if omega_a is not None else "null",
                json.dumps(apex_net) if apex_net is not None else "null",
                json.dumps(baseline_net) if baseline_net is not None else "null",
                json.dumps(alpha_ack),
                json.dumps(beta_bg),
                json.dumps(theta_stable_signals) if theta_stable_signals is not None else "null",
                json.dumps(theta_stable) if theta_stable is not None else "null",
                json.dumps(tao_signals) if tao_signals is not None else "null",
                critical_threshold,
            )
        )

else:

    _SCHEMA = "PGGArchonUltimateEvolutionFormulaReport/v1"
    _EVM_WEIGHTS = {
        "task_success": 0.25,
        "correctness": 0.20,
        "closure": 0.15,
        "reasoning_stability": 0.10,
        "tool_use": 0.10,
        "long_context_state": 0.10,
        "self_repair": 0.10,
    }
    _DELTA_WEIGHTS = {
        "hallucination": 20.0,
        "security": 20.0,
        "unclosed_debt": 15.0,
        "cost": 10.0,
        "latency": 8.0,
        "instability": 10.0,
        "memory_pollution": 7.0,
        "tool_risk": 5.0,
        "governance_debt": 5.0,
    }
    _THETA_STABLE_WEIGHTS = {
        "psi_practice_knowledge_unity": 1.0 / 6.0,
        "lambda_causal_chain": 1.0 / 6.0,
        "gamma_self_healing_allocation": 1.0 / 6.0,
        "xi_deterministic_execution": 1.0 / 6.0,
        "phi_closed_loop_control": 1.0 / 6.0,
        "upsilon_resource_harmony": 1.0 / 6.0,
    }

    def _finite(value: Any, *, default: float = 0.0, low: float | None = None, high: float | None = None) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = default
        if not math.isfinite(numeric):
            numeric = default
        if low is not None:
            numeric = max(low, numeric)
        if high is not None:
            numeric = min(high, numeric)
        return numeric

    def _as_mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    def compute_evm_full(signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        src = _as_mapping(signals)
        components: Dict[str, float] = {}
        for name in _EVM_WEIGHTS:
            components[name] = _finite(src.get(name), default=50.0, low=0.0, high=100.0)
        score = round(sum(components[name] * weight for name, weight in _EVM_WEIGHTS.items()), 3)
        return {"score": score, "components": components, "weights": dict(_EVM_WEIGHTS)}

    def compute_sigma_delta(delta_signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        src = _as_mapping(delta_signals)
        components: Dict[str, float] = {}
        for name, weight in _DELTA_WEIGHTS.items():
            severity = _finite(src.get(name), default=0.0, low=0.0, high=1.0)
            components[name] = round(severity * weight, 3)
        score = round(sum(components.values()), 3)
        critical = src.get("critical")
        critical_active = bool(critical) or any(
            _finite(src.get(key), low=0.0) >= 1.0
            for key in ("p0", "critical_security", "credential_leak", "false_completion")
        )
        return {
            "score": min(score, 100.0),
            "raw_score": score,
            "components": components,
            "weights": dict(_DELTA_WEIGHTS),
            "critical_active": critical_active,
        }

    def compute_omega_a(value: Any = None, *, apex_net: Any = None, baseline_net: Any = None) -> Dict[str, Any]:
        if apex_net is not None and baseline_net is not None:
            baseline = _finite(baseline_net, default=0.0)
            apex = _finite(apex_net, default=0.0)
            if abs(baseline) < 0.001:
                raw = 1.0
                source = "baseline_unusable_default_1"
            else:
                raw = apex / baseline
                source = "net_score_ratio"
        else:
            raw = _finite(value, default=1.0)
            source = "direct_or_default"
        bounded = round(max(0.5, min(2.0, raw)), 3)
        return {"value": bounded, "raw_value": round(raw, 6), "source": source, "bounds": [0.5, 2.0]}

    def compute_theta_stable(signals: Mapping[str, Any] | None = None, *, direct_value: Any = None) -> Dict[str, Any]:
        if direct_value is not None:
            raw_direct = _finite(direct_value, default=1.0, low=0.0, high=2.0)
            return {
                "value": round(max(0.5, min(2.0, raw_direct)), 3),
                "raw_score": round(raw_direct * 100.0, 3),
                "source": "direct_theta_value",
                "components": {},
                "weights": dict(_THETA_STABLE_WEIGHTS),
                "kernel_factors": ["Ψ", "Λ", "Γ", "Ξ", "Φ", "Υ"],
            }
        src = _as_mapping(signals)
        components: Dict[str, float] = {}
        for name in _THETA_STABLE_WEIGHTS:
            components[name] = _finite(src.get(name), default=75.0, low=0.0, high=100.0)
        raw_score = sum(components[name] * weight for name, weight in _THETA_STABLE_WEIGHTS.items())
        multiplier = 0.5 + (raw_score / 100.0) * 1.5
        return {
            "value": round(max(0.5, min(2.0, multiplier)), 3),
            "raw_score": round(raw_score, 3),
            "source": "six_dimensional_theta_stable",
            "components": components,
            "weights": dict(_THETA_STABLE_WEIGHTS),
            "kernel_factors": ["Ψ", "Λ", "Γ", "Ξ", "Φ", "Υ"],
        }

    def build_ultimate_evolution_formula_report(
        *,
        evm_signals: Mapping[str, Any] | None = None,
        delta_signals: Mapping[str, Any] | None = None,
        omega_a: Any = None,
        apex_net: Any = None,
        baseline_net: Any = None,
        alpha_ack: Any = 1.0,
        beta_bg: Any = 1.0,
        theta_stable_signals: Mapping[str, Any] | None = None,
        theta_stable: Any = None,
        tao_signals: Mapping[str, Any] | None = None,
        critical_threshold: float = 1.0,
        source: str = "pgg_archon_ultimate_evolution_formula",
    ) -> Dict[str, Any]:
        evm = compute_evm_full(evm_signals)
        delta = compute_sigma_delta(delta_signals)
        omega = compute_omega_a(omega_a, apex_net=apex_net, baseline_net=baseline_net)
        alpha = _finite(alpha_ack, default=1.0, low=0.0, high=2.0)
        beta = _finite(beta_bg, default=1.0, low=0.0, high=2.0)
        theta = compute_theta_stable(theta_stable_signals, direct_value=theta_stable)
        tao = _as_mapping(tao_signals)
        tao_mults = {
            "A": _finite(tao.get("A"), default=1.0, low=0.0, high=2.0),
            "B": _finite(tao.get("B"), default=1.0, low=0.0, high=2.0),
            "tdhlgwb": _finite(tao.get("tdhlgwb"), default=1.0, low=0.0, high=2.0),
        }
        tao_product = 1.0
        for val in tao_mults.values():
            tao_product *= val
        raw_score = omega["value"] * alpha * beta * theta["value"] * tao_product * evm["score"] - delta["score"]
        critical_active = bool(delta["critical_active"] and critical_threshold <= 1.0)
        score = 0.0 if critical_active else max(0.0, min(100.0, raw_score))
        status = "BLOCKED" if critical_active else ("PASS" if score >= 75 else "WATCH" if score >= 50 else "HOLD")
        blockers = []
        if critical_active:
            blockers.append("p0_critical_delta_fuse_triggered")
        return {
            "schema": _SCHEMA,
            "formula_name": "APEX Ultimate 终极进化公式",
            "status": status,
            "score": round(score, 3),
            "raw_score": round(raw_score, 3),
            "omega_a": omega,
            "alpha_ack": round(alpha, 3),
            "beta_bg": round(beta, 3),
            "theta_stable": theta,
            "tao_multipliers": {k: round(v, 3) for k, v in tao_mults.items()},
            "evm_full": evm,
            "sigma_delta_all": delta,
            "critical_fuse": {"enabled": True, "active": critical_active, "threshold": critical_threshold},
            "blockers": blockers,
            "source": source,
            "ts": time.time(),
            "side_effects": "read_only_report",
            "capability_boundary": "候选评分基因；不证明AGI完成；正式接管核心前需真实基线、自动采集、P0熔断和回滚门禁。",
        }


def main() -> int:
    """CLI entry point for SE25 Ultimate Evolution Formula gate."""
    import json, sys
    report = build_ultimate_evolution_formula_report()
    if "--pretty" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()


__all__ = [
    "build_ultimate_evolution_formula_report",
    "compute_evm_full",
    "compute_omega_a",
    "compute_theta_stable",
    "compute_sigma_delta",
]