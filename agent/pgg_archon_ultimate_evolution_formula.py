"""PGG Archon ultimate evolution formula sidecar.

This module embeds the user-named "终极进化公式" into Hermes Agent as a
bounded, read-only scoring surface:

    APEX_AK = Ω_A · EVM_full - ΣΔ_all

It deliberately does not mutate the agent loop, provider routing, memory,
skills, tools, credentials, or gene stores.  It is designed to be consumed by
native Hermes surfaces such as reports, cron jobs, skills, tools, SessionDB
summaries, and later guarded promotion gates.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, Mapping, Sequence

_SCHEMA = "PGGArchonUltimateEvolutionFormulaReport/v1"
_ARS_SCHEMA = "PGGArchonUltimateEvolutionARSPlan/v1"

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

_DEFAULT_MODEL_ROLES = (
    {"provider": "gpt55_5yuantoken", "model": "gpt-5.5", "role": "primary_synthesizer", "weight": 0.40},
    {"provider": "claude_opus47_5yuantoken", "model": "claude-opus-4-7", "role": "code_architecture_critic", "weight": 0.25},
    {"provider": "deepseek_v4_flash", "model": "deepseek-v4-flash", "role": "logic_and_cn_legal_reasoning_critic", "weight": 0.20},
    {"provider": "minimax_m27_highspeed", "model": "MiniMax-M2.7-highspeed", "role": "cheap_broad_reviewer", "weight": 0.15},
)


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


def _score_status(value: Any) -> float:
    text = str(value or "").upper()
    if text in {"PASS", "OK", "READY", "HEALTHY"}:
        return 1.0
    if text in {"WATCH", "WARN", "BYPASSED", "PARTIAL"}:
        return 0.65
    if text in {"BLOCK", "BLOCKED", "ERROR", "FAIL", "HOLD"}:
        return 0.2
    return 0.5


def _ratio(value: Any, *, inverse: bool = False, scale: float = 10.0) -> float:
    numeric = _finite(value, default=0.0, low=0.0)
    if inverse:
        return 1.0 / (1.0 + numeric / max(scale, 0.001))
    return min(1.0, numeric / max(scale, 0.001))


def compute_evm_full(signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Compute bounded EVM_full from normalized 0..100 sub-signals."""
    src = _as_mapping(signals)
    components: Dict[str, float] = {}
    for name in _EVM_WEIGHTS:
        components[name] = _finite(src.get(name), default=50.0, low=0.0, high=100.0)
    score = round(sum(components[name] * weight for name, weight in _EVM_WEIGHTS.items()), 3)
    return {"score": score, "components": components, "weights": dict(_EVM_WEIGHTS)}


def compute_sigma_delta(delta_signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Compute ΣΔ_all as normalized 0..100 debt/risk deduction."""
    src = _as_mapping(delta_signals)
    components: Dict[str, float] = {}
    for name, weight in _DELTA_WEIGHTS.items():
        severity = _finite(src.get(name), default=0.0, low=0.0, high=1.0)
        components[name] = round(severity * weight, 3)
    score = round(sum(components.values()), 3)
    critical = src.get("critical")
    critical_active = bool(critical) or any(_finite(src.get(key), low=0.0) >= 1.0 for key in ("p0", "critical_security", "credential_leak", "false_completion"))
    return {
        "score": min(score, 100.0),
        "raw_score": score,
        "components": components,
        "weights": dict(_DELTA_WEIGHTS),
        "critical_active": critical_active,
    }


def compute_omega_a(value: Any = None, *, apex_net: Any = None, baseline_net: Any = None) -> Dict[str, Any]:
    """Compute bounded Ω_A from direct value or baseline comparison."""
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


def build_ultimate_evolution_formula_report(
    *,
    evm_signals: Mapping[str, Any] | None = None,
    delta_signals: Mapping[str, Any] | None = None,
    omega_a: Any = None,
    apex_net: Any = None,
    baseline_net: Any = None,
    critical_threshold: float = 1.0,
    source: str = "pgg_archon_ultimate_evolution_formula",
) -> Dict[str, Any]:
    """Build a read-only report for the 终极进化公式."""
    evm = compute_evm_full(evm_signals)
    delta = compute_sigma_delta(delta_signals)
    omega = compute_omega_a(omega_a, apex_net=apex_net, baseline_net=baseline_net)
    raw_score = omega["value"] * evm["score"] - delta["score"]
    critical_active = bool(delta["critical_active"] and critical_threshold <= 1.0)
    score = 0.0 if critical_active else max(0.0, min(100.0, raw_score))
    status = "BLOCKED" if critical_active else ("PASS" if score >= 75 else "WATCH" if score >= 50 else "HOLD")
    blockers = []
    if critical_active:
        blockers.append("p0_critical_delta_fuse_triggered")
    if omega["source"] == "direct_or_default" and omega["raw_value"] != 1.0:
        blockers.append("omega_a_direct_value_requires_external_validation")
    return {
        "schema": _SCHEMA,
        "formula_name": "终极进化公式",
        "formula": "APEX_AK = Ω_A · EVM_full - ΣΔ_all",
        "status": status,
        "score": round(score, 3),
        "raw_score": round(raw_score, 3),
        "omega_a": omega,
        "evm_full": evm,
        "sigma_delta_all": delta,
        "critical_fuse": {"enabled": True, "active": critical_active, "threshold": critical_threshold},
        "blockers": blockers,
        "source": source,
        "ts": time.time(),
        "side_effects": "read_only_report",
        "capability_boundary": "候选评分基因；不证明AGI完成；正式接管核心前需真实基线、自动采集、P0熔断和回滚门禁。",
    }


def build_ars_driver_plan(
    report: Mapping[str, Any],
    *,
    model_roles: Sequence[Mapping[str, Any]] = _DEFAULT_MODEL_ROLES,
) -> Dict[str, Any]:
    """Build a native Hermes ARS plan driven by the formula report.

    The plan is declarative and side-effect-free: cron/jobs/tools may consume it
    later, but this function never calls providers or edits the core loop.
    """
    rep = _as_mapping(report)
    score = _finite(rep.get("score"), default=0.0, low=0.0, high=100.0)
    status = str(rep.get("status") or "UNKNOWN")
    actions = [
        "collect_native_evidence_from_sessiondb_tools_cron_and_gateway",
        "gpt55_primary_synthesis_with_responses_api",
        "claude_code_architecture_critique_with_responses_api",
        "deepseek_logic_cn_reasoning_review",
        "minimax_low_cost_broad_review",
        "synthesize_repair_candidates_without_core_loop_mutation",
        "run_tests_and_quality_gate_before_any_promotion",
    ]
    if status == "BLOCKED":
        decision = "halt_and_repair_p0_delta"
    elif score >= 75:
        decision = "allow_low_risk_sidecar_iteration"
    elif score >= 50:
        decision = "watch_collect_more_evidence"
    else:
        decision = "hold_no_promotion"
    return {
        "schema": _ARS_SCHEMA,
        "formula_schema": rep.get("schema"),
        "decision": decision,
        "primary_model": "gpt55_5yuantoken/gpt-5.5",
        "model_roles": [dict(item) for item in model_roles],
        "native_hermes_surfaces": ["skills", "tools", "cron", "plugins", "SessionDB", "provider_routing", "workspace_reports"],
        "actions": actions,
        "side_effects": "read_only_plan",
        "requires_human_authorization_before_core_loop_patch": True,
    }


def build_report_from_runtime_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Map existing PGG/APEX runtime status into the ultimate formula surface."""
    src = _as_mapping(status)
    quality = _as_mapping(src.get("quality_gate"))
    health = _as_mapping(src.get("health_report"))
    formula = _as_mapping(src.get("formula_report"))
    meta = _as_mapping(src.get("meta_evolution_report"))
    cron = _as_mapping(src.get("cron_dryrun"))
    evm_signals = {
        "task_success": 100.0 * _score_status(quality.get("status")),
        "correctness": 100.0 * _score_status(formula.get("status")),
        "closure": 100.0 * _score_status(src.get("promotion_lifecycle_gate", {}).get("status") if isinstance(src.get("promotion_lifecycle_gate"), Mapping) else None),
        "reasoning_stability": 100.0 * _score_status(meta.get("status")),
        "tool_use": 100.0 * _score_status(health.get("status")),
        "long_context_state": 100.0 if src.get("schema") else 50.0,
        "self_repair": 100.0 * _score_status(src.get("gene_lifecycle_gate", {}).get("status") if isinstance(src.get("gene_lifecycle_gate"), Mapping) else None),
    }
    delta_signals = {
        "hallucination": 1.0 - _score_status(formula.get("status")),
        "security": 1.0 - _score_status(src.get("security_report", {}).get("status") if isinstance(src.get("security_report"), Mapping) else "PASS"),
        "unclosed_debt": _ratio(src.get("stable_ready_unresolved_count"), scale=5.0),
        "cost": 0.0,
        "latency": 0.0,
        "instability": 1.0 - _score_status(meta.get("status")),
        "memory_pollution": 0.0,
        "tool_risk": 0.0 if _score_status(health.get("status")) >= 0.65 else 0.5,
        "governance_debt": _ratio(cron.get("bad_lines"), scale=3.0),
        "critical": bool(src.get("p0_blocked") or src.get("critical_blocked")),
    }
    return build_ultimate_evolution_formula_report(evm_signals=evm_signals, delta_signals=delta_signals, omega_a=1.0, source="runtime_status_mapping")


__all__ = [
    "build_ultimate_evolution_formula_report",
    "build_ars_driver_plan",
    "build_report_from_runtime_status",
    "compute_evm_full",
    "compute_omega_a",
    "compute_sigma_delta",
]
