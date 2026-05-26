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


def build_formula_report_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose formula readiness without pretending live telemetry exists."""
    return build_apex_formula_report({})


__all__ = [
    "FORMULA_SOURCES",
    "STANDARD_V23_FIELDS",
    "V10_FINAL_FIELDS",
    "build_apex_formula_report",
    "build_formula_report_from_runtimeos_status",
    "dg_v10_final_score",
    "dg_v2_3_score",
]
