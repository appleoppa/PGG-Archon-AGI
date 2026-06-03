"""Dedicated tests for promoted PGG Archon Delta-G gate.

Boundary: validates pure scoring/classification behavior only. It does not prove
legal correctness, provider participation, runtime deployment, or full AGI.
"""
from __future__ import annotations

import pytest

from agent.pgg_archon_delta_gate import (
    DeltaGInputs,
    DeltaGResult,
    MeasurementResult,
    ParameterMeasurement,
    apply_delta_gate,
    calc_delta_g,
    judge_state,
    run_anti_hallucination,
)


def test_delta_g_inputs_compatibility_path_is_bounded() -> None:
    compat_result = calc_delta_g(
        DeltaGInputs(
            alpha_ack=1.0,
            beta_bg=1.0,
            theta_stable=1.0,
            evm_score=1.0,
            tao_alignment=1.0,
            delta_sigma=0.0,
        )
    )
    assert isinstance(compat_result, tuple)
    total, terms = compat_result
    assert total == 0.0
    assert terms["positive_average"] == 1.0
    assert judge_state(total) == "allowed"


def test_delta_g_inputs_reject_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        DeltaGInputs(alpha_ack=1.1)
    with pytest.raises(ValueError):
        DeltaGInputs(delta_sigma=-0.1)
    with pytest.raises(TypeError):
        DeltaGInputs(beta_bg="bad")  # type: ignore[arg-type]


def test_measurement_result_legacy_path_and_gate_classification() -> None:
    measurement = MeasurementResult(
        parameters={
            "citation_accuracy": ParameterMeasurement("citation_accuracy", 1.0, 1.0),
            "legal_term_consistency": ParameterMeasurement("legal_term_consistency", 1.0, 1.0),
            "logical_coherence": ParameterMeasurement("logical_coherence", 1.0, 1.0),
            "numerical_reasonability": ParameterMeasurement("numerical_reasonability", 1.0, 1.0),
            "temporal_consistency": ParameterMeasurement("temporal_consistency", 1.0, 1.0),
            "source_attribution": ParameterMeasurement("source_attribution", 1.0, 1.0),
            "factual_density": ParameterMeasurement("factual_density", 1.0, 1.0),
            "noise_ratio": ParameterMeasurement("noise_ratio", 1.0, 1.0),
            "fidelity_score": ParameterMeasurement("fidelity_score", 1.0, 1.0),
            "logic_chain_strength": ParameterMeasurement("logic_chain_strength", 1.0, 1.0),
            "context_relevance": ParameterMeasurement("context_relevance", 1.0, 1.0),
        },
        raw_text_length=0,
        measurement_method="unit_test",
    )
    result = calc_delta_g(measurement)
    assert isinstance(result, DeltaGResult)
    assert result.total == 0.0
    gate = apply_delta_gate(result)
    assert gate.state == "allowed"
    assert gate.is_allowed


def test_judge_state_thresholds() -> None:
    assert judge_state(0.0) == "allowed"
    assert judge_state(0.29) == "allowed"
    assert judge_state(0.30) == "partial_repair"
    assert judge_state(0.59) == "partial_repair"
    assert judge_state(0.60) == "full_heal"
    assert judge_state(1.0) == "full_heal"


def test_run_anti_hallucination_smoke_for_stable_legal_text() -> None:
    text = "根据《民法典》第577条，当事人一方不履行合同义务，应当承担违约责任。"
    gate = run_anti_hallucination(text)
    assert gate.state in {"allowed", "partial_repair", "full_heal"}
    assert 0.0 <= gate.delta_g.total <= 1.0
    assert gate.delta_g.measurement.raw_text_length == len(text)
