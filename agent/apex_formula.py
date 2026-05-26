"""APEX RuntimeOS formula scoring helpers.

This module extracts a deterministic, bounded subset of the historical APEX
v2.3 / V10 formula materials into RuntimeOS.  It is read-only: no files,
runtime state, memory, or gene stores are changed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Mapping

STANDARD_V23_FIELDS = (
    "ΔG_base", "Θ", "K", "ε", "Φ", "Ψ", "Π", "Λ_ctx", "Γ",
    "PID", "RD", "Kelly", "E_xp", "M_meta", "Ξ",
)

V10_FINAL_FIELDS = (
    "ΔG_base", "Π", "PID", "RD", "Kelly", "Γ", "E_xp", "M", "Λ_sw", "Ξ",
)

FORMULA_SOURCES = {
    "v2_3": "external/github-evolution/formulas/apex_v2_1_fixed.py",
    "v10_4_final": "external/z-dashen/apex/apex-spiral/ApexSpiral/APEX_V10_FORMULA.md#第十三层",
}


def _finite_number(value: Any, *, field: str, default: float | None = None) -> float:
    if value is None and default is not None:
        return default
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be finite")
    return numeric


def _non_negative(value: Any, *, field: str, default: float | None = None) -> float:
    numeric = _finite_number(value, field=field, default=default)
    if numeric < 0.0:
        raise ValueError(f"{field} must be >= 0")
    return numeric


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def dg_v2_3_score(params: Mapping[str, Any] | None = None) -> float:
    """Calculate the bounded APEX v2.3 ΔG score.

    This is a safe reimplementation of the v2.3 source formula.  Defaults are
    conservative and match the archived formula's fallback values.
    """
    p = params or {}
    l_ctx = _non_negative(p.get("Λ_ctx"), field="Λ_ctx", default=0.5)
    kelly_raw = _clamp(_non_negative(p.get("Kelly"), field="Kelly", default=0.5), 0.0, 1.0)
    gamma_raw = _non_negative(p.get("Γ"), field="Γ", default=0.5)
    gamma_f = max(math.sqrt(max(gamma_raw, 0.001) / 0.5), 0.1)
    e_xp_val = _non_negative(p.get("E_xp"), field="E_xp", default=0.5)
    m_val = _non_negative(p.get("M_meta"), field="M_meta", default=0.5)
    xi_val = max(_non_negative(p.get("Ξ"), field="Ξ", default=0.5), 0.1)
    pid_val = _non_negative(p.get("PID"), field="PID", default=0.5)

    pi_raw = max(_non_negative(p.get("Π"), field="Π", default=0.5), 0.1)
    p_parallel = 0.8
    pi_effective = 1.0 / ((1 - p_parallel) + p_parallel / pi_raw)
    pi_eff = pi_effective / (1 + l_ctx)

    alpha_couple = 0.3
    eps = 0.001
    delta_exp_mem = 1.0 - alpha_couple * min(e_xp_val, m_val) / (e_xp_val + m_val + eps)
    e_xp_adjusted = e_xp_val * delta_exp_mem
    m_adjusted = m_val * delta_exp_mem

    if kelly_raw < 0.4:
        kelly_gate = (kelly_raw / 0.4) ** 2
    else:
        kelly_gate = 1.0
    kelly_bonus = 1.0 + max(0.0, (kelly_raw - 0.4) / 0.4 * 0.3)
    exp_decisions = max(_non_negative(p.get("_n_decisions"), field="_n_decisions", default=10.0), 0.0)
    kelly_decay = 1.0 - math.exp(-exp_decisions / 5.0)
    kelly_adjusted = 0.4 * (1 - kelly_decay) + kelly_raw * kelly_decay

    layer1 = (
        _non_negative(p.get("ΔG_base"), field="ΔG_base", default=0.5)
        * _non_negative(p.get("Θ"), field="Θ", default=0.5)
        * _non_negative(p.get("K"), field="K", default=0.5)
        * _non_negative(p.get("ε"), field="ε", default=0.5)
    )
    layer2 = _non_negative(p.get("Φ"), field="Φ", default=0.5) * _non_negative(p.get("Ψ"), field="Ψ", default=0.5) * pi_eff * gamma_f
    layer3 = pid_val * _non_negative(p.get("RD"), field="RD", default=0.5) * kelly_gate * kelly_bonus * kelly_adjusted
    layer4 = e_xp_adjusted * m_adjusted * xi_val * gamma_f

    bio_keys = ("Ψ_evolve", "Φ_bio", "Ξ_gene", "Σ_entropy", "Υ_energy", "Λ_field")
    ai_keys = ("Ω_chem", "ΔG_chem", "K_eq", "ΔW_syn", "Ψ_nerve", "H_rhythm", "Θ_feat", "∇*_θ", "Γ_cross", "ℛ_ai", "Ψ_quan", "Ω_quan", "C_claw", "V_gdp")
    bio_terms = [_non_negative(p[key], field=key) for key in bio_keys if key in p and p[key] is not None]
    ai_terms = [_non_negative(p[key], field=key) for key in ai_keys if key in p and p[key] is not None]
    layer5 = math.prod(bio_terms) ** (1.0 / len(bio_terms)) if bio_terms else 1.0
    layer6 = math.prod(ai_terms) ** (1.0 / len(ai_terms)) if ai_terms else 1.0

    all_vals = [_non_negative(p.get(key), field=key, default=0.5) for key in STANDARD_V23_FIELDS]
    all_vals.extend(bio_terms)
    all_vals.extend(ai_terms)
    positive_vals = [value for value in all_vals if value > 0]
    if positive_vals:
        mean = sum(positive_vals) / len(positive_vals)
        variance = sum((value - mean) ** 2 for value in positive_vals) / len(positive_vals)
        coherence = max(0.0, 1.0 - math.sqrt(variance))
    else:
        coherence = 1.0

    layers = [max(layer, 0.0) for layer in (layer1, layer2, layer3, layer4, layer5, layer6) if layer != 1.0]
    if not layers:
        return 0.0
    raw = math.prod(layers) ** (1.0 / len(layers))
    return round(min(raw * (0.5 + 0.5 * coherence), 10.0), 6)


def dg_v10_final_score(params: Mapping[str, Any] | None = None) -> float:
    """Calculate the V10.4 第十三层 ΔG_final product with validation."""
    p = params or {}
    defaults = {
        "ΔG_base": 0.49,
        "Π": 4.0,
        "PID": 0.96,
        "RD": 0.88,
        "Kelly": 0.44,
        "Γ": 0.29,
        "E_xp": 1.20,
        "M": 1.08,
        "Λ_sw": 0.90,
        "Ξ": 0.52,
    }
    result = 1.0
    for field in V10_FINAL_FIELDS:
        result *= _non_negative(p.get(field), field=field, default=defaults[field])
    return round(result, 6)


def build_apex_formula_report(params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Build a read-only APEX formula report from sanitized numeric params."""
    source = params or {}
    v23_score = dg_v2_3_score(source)
    raw_v10_source = source.get("v10")
    v10_source: Mapping[str, Any] = raw_v10_source if isinstance(raw_v10_source, Mapping) else source
    v10_score = dg_v10_final_score(v10_source)
    missing_v23 = [field for field in STANDARD_V23_FIELDS if field not in source]
    missing_v10 = [field for field in V10_FINAL_FIELDS if field not in v10_source]
    status = "PASS" if not missing_v23 and not missing_v10 else "WARN"
    return {
        "schema": "ApexRuntimeOSFormulaReport/v1",
        "status": status,
        "v2_3_score": v23_score,
        "v10_final_score": v10_score,
        "missing_v2_3_fields": missing_v23,
        "missing_v10_fields": missing_v10,
        "sources": FORMULA_SOURCES,
        "boundary": "APEX v2.3 is executable; V10.4 is currently limited to the validated 第十三层 product subset.",
        "side_effects": "read_only_report",
    }


def _status_factor(value: Any, *, positive: set[str] | None = None) -> float:
    text = str(value or "").upper()
    good = positive or {"PASS", "OK"}
    if text in good:
        return 1.0
    if text in {"WARN", "WATCH", "BYPASSED"}:
        return 0.65
    if text in {"BLOCK", "HOLD", "ERROR"}:
        return 0.25
    return 0.5


def _ratio_from_count(count: Any, *, scale: float = 10.0, inverse: bool = False) -> float:
    try:
        numeric = max(0.0, float(count or 0.0))
    except (TypeError, ValueError):
        numeric = 0.0
    value = 1.0 / (1.0 + numeric / max(scale, 0.001)) if inverse else min(1.0 + numeric / max(scale, 0.001), 5.0)
    return round(max(0.1, value), 6)


def _extract_runtimeos_formula_params(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Map aggregate RuntimeOS state into bounded formula parameters.

    Only aggregate counters and gate statuses are used. No prompts, messages,
    local paths, credentials, or external code are read or executed.
    """
    required_keys = {"schema", "health_report", "cron_dryrun", "promotion_lifecycle_gate"}
    if not required_keys.issubset(set(status.keys())):
        return {}

    health_raw = status.get("health_report")
    health: Mapping[str, Any] = health_raw if isinstance(health_raw, Mapping) else {}
    cron_raw = status.get("cron_dryrun")
    cron: Mapping[str, Any] = cron_raw if isinstance(cron_raw, Mapping) else {}
    promotion_gate_raw = status.get("promotion_lifecycle_gate")
    promotion_gate: Mapping[str, Any] = promotion_gate_raw if isinstance(promotion_gate_raw, Mapping) else {}
    evm_raw = status.get("evm_gate")
    evm_gate: Mapping[str, Any] = evm_raw if isinstance(evm_raw, Mapping) else {}
    sequence_raw = status.get("sequence_gate")
    sequence_gate: Mapping[str, Any] = sequence_raw if isinstance(sequence_raw, Mapping) else {}
    gene_raw = status.get("gene_lifecycle_gate")
    gene_gate: Mapping[str, Any] = gene_raw if isinstance(gene_raw, Mapping) else {}
    quality_raw = status.get("quality_gate")
    quality_gate: Mapping[str, Any] = quality_raw if isinstance(quality_raw, Mapping) else {}

    health_factor = _status_factor(health.get("status"), positive={"OK"})
    bad_line_factor = _ratio_from_count(cron.get("bad_lines"), scale=3.0, inverse=True)
    rollback_factor = _ratio_from_count(status.get("pending_rollbacks"), scale=3.0, inverse=True)
    unresolved_factor = _ratio_from_count(status.get("stable_ready_unresolved_count"), scale=3.0, inverse=True)
    evm_value = evm_gate.get("evm_value")
    if not isinstance(evm_value, (int, float)):
        evm_value = 0.5
    evm_factor = max(0.1, min(float(evm_value), 10.0))
    sequence_factor = _status_factor(sequence_gate.get("status"))
    gene_factor = _status_factor(gene_gate.get("status"))
    promotion_factor = _status_factor(promotion_gate.get("status"))
    quality_factor = _status_factor(quality_gate.get("status"))
    mode_factor = 1.0 if status.get("mode") == "enforce" else 0.75
    cron_activity = _ratio_from_count(cron.get("unique_keys"), scale=10.0)
    candidate_factor = _ratio_from_count(status.get("candidate_groups"), scale=10.0)
    stable_factor = _ratio_from_count(status.get("stable_ready_count"), scale=10.0)
    promotion_count_factor = _ratio_from_count(status.get("promotion_count"), scale=10.0)

    params: Dict[str, Any] = {
        "ΔG_base": health_factor,
        "Θ": quality_factor,
        "K": rollback_factor,
        "ε": bad_line_factor,
        "Φ": promotion_factor,
        "Ψ": sequence_factor,
        "Π": max(0.1, cron_activity),
        "Λ_ctx": max(0.1, min(2.0, float(health.get("alert_count") or 0) / 10.0)),
        "Γ": evm_factor,
        "PID": unresolved_factor,
        "RD": gene_factor,
        "Kelly": min(1.0, max(0.1, promotion_factor * rollback_factor)),
        "E_xp": candidate_factor,
        "M_meta": stable_factor,
        "Ξ": mode_factor,
        "v10": {
            "ΔG_base": health_factor,
            "Π": max(0.1, cron_activity),
            "PID": unresolved_factor,
            "RD": gene_factor,
            "Kelly": min(1.0, max(0.1, promotion_factor * rollback_factor)),
            "Γ": evm_factor,
            "E_xp": candidate_factor,
            "M": promotion_count_factor,
            "Λ_sw": max(0.1, quality_factor),
            "Ξ": mode_factor,
        },
        "telemetry_source": "runtimeos_aggregate_status",
    }
    return params


def build_formula_report_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a read-only formula report from live aggregate RuntimeOS state."""
    params = _extract_runtimeos_formula_params(status)
    report = build_apex_formula_report(params)
    report["telemetry_source"] = params.get("telemetry_source", "missing_runtimeos_aggregate_status")
    report["live_params_used"] = bool(params)
    report["boundary"] = (
        report["boundary"]
        + " RuntimeOS integration uses aggregate counters/gate statuses only; it does not inspect prompts, paths, credentials, or execute external code."
    )
    return report


__all__ = [
    "FORMULA_SOURCES",
    "STANDARD_V23_FIELDS",
    "V10_FINAL_FIELDS",
    "build_apex_formula_report",
    "build_formula_report_from_runtimeos_status",
    "dg_v10_final_score",
    "dg_v2_3_score",
]
