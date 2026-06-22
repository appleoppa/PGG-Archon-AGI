"""PGG Archon SUPER-AGI formula — Rust PyO3 native bridge.

Read-only score/gate for the Ψ_SUPER_AGI formula.
Falls back to pure Python if native .so is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any, Dict, Mapping, Sequence

try:
    import hermes_pgg_super_agi_formula as _native
    _NATIVE = True
except ImportError:
    _NATIVE = False

_SCHEMA = "PGGArchonSuperAGIFormulaReport/v1"
_GATE_SCHEMA = "PGGArchonSuperAGIProgressiveGate/v1"

_DEFAULT_WEIGHTS = {
    "delta_g_apex": 1.0, "m_model": 1.0, "phi_mcp": 1.0,
    "f_github": 1.0, "s_fix": 1.0, "omega_rust_go": 1.0,
    "error_decay": 1.0, "hallucination_noise": 1.4, "system_drag": 1.0,
}

_REQUIRED_BOTTOM_SAFETY = {
    "manual_git_commit_review": True,
    "no_secret_reading": True,
    "no_production_skill_override": True,
    "no_core_loop_forced_modify": True,
    "no_untrusted_mcp_auto_register": True,
    "rollback_required": True,
}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _num(value: Any, default: float = 0.0, low: float = 0.0, high: float = 100.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        out = default
    if not math.isfinite(out):
        out = default
    return max(low, min(high, out))


def _unit(value: Any, default: float = 1.0) -> float:
    return _num(value, default=default, low=0.0, high=2.0)


def _fingerprint(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


if _NATIVE:
    def build_super_agi_formula_report(signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        s = signals if isinstance(signals, str) else json.dumps(signals if signals else {})
        return json.loads(_native.build_super_agi_formula_report(s))

    def build_super_agi_progressive_gate(
        report: Mapping[str, Any],
        requested_tier: str = "T0",
        safety: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        r = json.dumps(report if isinstance(report, str) else report)
        s = json.dumps(safety if safety else {})
        return json.loads(_native.build_super_agi_progressive_gate(r, requested_tier, s))
else:
    def build_super_agi_formula_report(signals: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        """Compute Ψ_SUPER_AGI engineering score from bounded signals (pure Python fallback)."""
        sig = dict(_mapping(signals))
        weights = dict(_DEFAULT_WEIGHTS)
        weights.update({k: _unit(v, default=weights.get(k, 1.0)) for k, v in _mapping(sig.get("weights")).items()})

        delta_g_apex = _num(sig.get("delta_g_apex"), default=75.0)
        m_model = _unit(sig.get("m_model"), default=1.0)
        phi_mcp = _unit(sig.get("phi_mcp"), default=1.0)
        f_github = _unit(sig.get("f_github"), default=0.5)
        s_fix = _num(sig.get("s_fix"), default=80.0)
        omega_rust_go = _unit(sig.get("omega_rust_go"), default=0.5)
        error_decay = _num(sig.get("error_decay"), default=10.0)
        hallucination_noise = _num(sig.get("hallucination_noise"), default=15.0)
        system_drag = _num(sig.get("system_drag"), default=10.0)

        spiral_gain = delta_g_apex * m_model * phi_mcp * f_github
        self_fix_kernel_gain = s_fix * omega_rust_go
        drag = (
            error_decay * weights["error_decay"]
            + hallucination_noise * weights["hallucination_noise"]
            + system_drag * weights["system_drag"]
        )
        raw_score = spiral_gain + self_fix_kernel_gain - drag
        normalized = max(0.0, min(100.0, raw_score / 2.0))

        report = {
            "schema": _SCHEMA,
            "formula": "Ψ_SUPER_AGI(t+1)=ΔG_APEX·M_provider·Φ_MCP·F_GitHub + S_fix·Ω_RustGo - Σ(ErrorDecay+HallucinationNoise+SystemDrag)",
            "inputs": {
                "delta_g_apex": delta_g_apex,
                "m_model": m_model,
                "phi_mcp": phi_mcp,
                "f_github": f_github,
                "s_fix": s_fix,
                "omega_rust_go": omega_rust_go,
                "error_decay": error_decay,
                "hallucination_noise": hallucination_noise,
                "system_drag": system_drag,
            },
            "components": {
                "spiral_gain": round(spiral_gain, 4),
                "self_fix_kernel_gain": round(self_fix_kernel_gain, 4),
                "drag": round(drag, 4),
                "raw_score": round(raw_score, 4),
                "normalized_score": round(normalized, 4),
            },
            "side_effects": "read_only_report",
            "capability_boundary": "Engineering score/gate only; not AGI completion, not core takeover, not production promotion.",
            "ts": time.time(),
        }
        report["fingerprint"] = _fingerprint(report)
        return report

    def build_super_agi_progressive_gate(
        report: Mapping[str, Any],
        requested_tier: str = "T0",
        safety: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Map formula score to Phase16 progressive authorization tiers (pure Python fallback)."""
        rep = _mapping(report)
        score = _num(_mapping(rep.get("components")).get("normalized_score"), default=0.0)
        requested = str(requested_tier or "T0").upper()
        safe = dict(_REQUIRED_BOTTOM_SAFETY)
        safe.update({k: bool(v) for k, v in _mapping(safety).items()})
        missing = [k for k, required in _REQUIRED_BOTTOM_SAFETY.items() if required and not safe.get(k)]

        blockers = []
        if missing:
            blockers.append({"code": "bottom_safety_missing", "items": missing})
        if requested in {"T4", "T5"}:
            blockers.append({"code": "human_review_required_for_runtime_or_production_tier", "requested_tier": requested})
        if score < 75.0:
            blockers.append({"code": "formula_score_below_75", "score": score})

        max_open_tier = "T3" if score >= 75.0 and not missing else "T1"
        status = "PASS" if not blockers and requested in {"T0", "T1", "T2", "T3"} else "HOLD"
        gate = {
            "schema": _GATE_SCHEMA,
            "status": status,
            "requested_tier": requested,
            "max_open_tier": max_open_tier,
            "score": score,
            "blockers": blockers,
            "allowed_actions": [
                "read_only_formula_scoring",
                "draft_gene_skill_test_gate",
                "candidate_discovery_scoring_quarantine",
                "isolated_rust_go_prototype_with_tests",
            ] if status == "PASS" else ["read_only_formula_scoring", "draft_only_report"],
            "forbidden_actions": [
                "git_commit_without_manual_review",
                "production_skill_override",
                "core_loop_forced_modify",
                "untrusted_mcp_auto_register",
                "untrusted_github_code_execute",
                "secret_reading_or_exposure",
            ],
            "side_effects": "read_only_gate",
            "ts": time.time(),
        }
        gate["fingerprint"] = _fingerprint(gate)
        return gate


__all__ = ["build_super_agi_formula_report", "build_super_agi_progressive_gate", "_NATIVE"]
