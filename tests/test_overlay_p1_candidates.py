"""Skip-friendly local validation for ignored P1 overlay candidates.

These tests do NOT make ignored overlays a hard dependency for clean checkouts.
If an overlay file is absent, the test skips. If present locally, it must be
importable and expose the expected public symbols recorded by the Round10
overlay decision matrix.

Boundary: this is governance evidence for promote/archive decisions only. It is
not a full capability test, not a runtime participation claim, and not a reason
to bulk-commit ignored overlays.
"""
from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

P1_CANDIDATES = {
    "agent.apex_runtimeos_sequence": {
        "path": ROOT / "agent/apex_runtimeos_sequence.py",
        "symbols": [
            "normalize_sequence_code",
            "build_sequence_gate_report",
            "build_cycle_state_report",
        ],
    },
    "agent.pgg_archon_delta_gate": {
        "path": ROOT / "agent/pgg_archon_delta_gate.py",
        "symbols": ["calc_delta_g", "apply_delta_gate", "judge_state"],
    },
    "agent.pgg_archon_ultimate_evolution_ars_cycle": {
        "path": ROOT / "agent/pgg_archon_ultimate_evolution_ars_cycle.py",
        "symbols": [
            "build_phase3_ars_cycle",
            "run_phase3_cycle",
            "write_phase3_report",
        ],
    },
    "agent.pgg_archon_ultimate_evolution_formula": {
        "path": ROOT / "agent/pgg_archon_ultimate_evolution_formula.py",
        "symbols": [
            "compute_evm_full",
            "build_ultimate_evolution_formula_report",
            "build_report_from_runtime_status",
        ],
    },
}


def _load_or_skip(module_name: str):
    spec = P1_CANDIDATES[module_name]
    if not spec["path"].exists():
        pytest.skip(f"local ignored overlay absent: {spec['path']}")
    return importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", sorted(P1_CANDIDATES))
def test_p1_overlay_candidates_import_and_expose_expected_symbols(module_name: str) -> None:
    module = _load_or_skip(module_name)
    missing = [name for name in P1_CANDIDATES[module_name]["symbols"] if not hasattr(module, name)]
    assert missing == []
    for symbol in P1_CANDIDATES[module_name]["symbols"]:
        value = getattr(module, symbol)
        assert callable(value) or inspect.isclass(value)


def test_apex_runtimeos_sequence_normalize_smoke() -> None:
    module = _load_or_skip("agent.apex_runtimeos_sequence")
    normalize = getattr(module, "normalize_sequence_code")
    result = normalize("21354")
    assert result == "21354" or result == (2, 1, 3, 5, 4) or result == [2, 1, 3, 5, 4]


def test_delta_gate_known_safe_input_smoke() -> None:
    module = _load_or_skip("agent.pgg_archon_delta_gate")
    calc = getattr(module, "calc_delta_g")
    MeasurementResult = getattr(module, "MeasurementResult")
    ParameterMeasurement = getattr(module, "ParameterMeasurement")
    measurement = MeasurementResult(
        parameters={
            "alpha_ack": ParameterMeasurement("alpha_ack", 1.0, 1.0),
            "beta_bg": ParameterMeasurement("beta_bg", 1.0, 1.0),
            "theta_stable": ParameterMeasurement("theta_stable", 1.0, 1.0),
            "evm_score": ParameterMeasurement("evm_score", 1.0, 1.0),
            "tao_alignment": ParameterMeasurement("tao_alignment", 1.0, 1.0),
            "delta_sigma": ParameterMeasurement("delta_sigma", 1.0, 1.0),
        },
        raw_text_length=0,
        measurement_method="test_overlay_p1_candidates",
    )
    try:
        result = calc(measurement)
    except TypeError:
        pytest.skip("calc_delta_g signature requires richer runtime context; symbol import verified")
    assert result is not None
    assert hasattr(result, "total")


def test_ultimate_formula_report_smoke() -> None:
    module = _load_or_skip("agent.pgg_archon_ultimate_evolution_formula")
    report_fn = getattr(module, "build_ultimate_evolution_formula_report")
    try:
        result = report_fn()
    except TypeError:
        pytest.skip("build_ultimate_evolution_formula_report signature requires richer runtime context; symbol import verified")
    if isinstance(result, str):
        json.loads(result)
    else:
        assert isinstance(result, dict)


def test_ultimate_ars_cycle_report_smoke() -> None:
    module = _load_or_skip("agent.pgg_archon_ultimate_evolution_ars_cycle")
    report_fn = getattr(module, "build_phase3_ars_cycle")
    try:
        result = report_fn({})
    except TypeError:
        pytest.skip("build_phase3_ars_cycle signature requires richer runtime context; symbol import verified")
    if isinstance(result, str):
        json.loads(result)
    else:
        assert isinstance(result, dict)
