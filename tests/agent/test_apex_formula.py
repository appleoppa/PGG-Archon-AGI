from __future__ import annotations

import math

import pytest

from agent.apex_formula import (
    STANDARD_V23_FIELDS,
    V10_FINAL_FIELDS,
    build_apex_formula_report,
    build_formula_report_from_runtimeos_status,
    dg_v10_final_score,
    dg_v2_3_score,
)


V23_PARAMS = {
    "ΔG_base": 0.49,
    "Θ": 0.8,
    "K": 0.7,
    "ε": 0.9,
    "Φ": 0.85,
    "Ψ": 0.75,
    "Π": 4.0,
    "Λ_ctx": 0.3,
    "Γ": 0.5,
    "PID": 0.96,
    "RD": 0.88,
    "Kelly": 0.44,
    "E_xp": 1.2,
    "M_meta": 1.08,
    "Ξ": 0.52,
}


def test_v10_final_score_matches_archived_product():
    score = dg_v10_final_score({})
    expected = 0.49 * 4.0 * 0.96 * 0.88 * 0.44 * 0.29 * 1.20 * 1.08 * 0.90 * 0.52
    assert score == round(expected, 6)
    assert math.isclose(score, expected, rel_tol=0.000001)
    assert math.isclose(score, 0.129, rel_tol=0.01)


def test_v23_score_is_bounded_and_deterministic():
    first = dg_v2_3_score(V23_PARAMS)
    second = dg_v2_3_score(dict(V23_PARAMS))
    assert first == second
    assert 0.0 <= first <= 10.0


def test_v23_score_rejects_negative_values():
    bad = dict(V23_PARAMS)
    bad["Π"] = -1
    with pytest.raises(ValueError):
        dg_v2_3_score(bad)


def test_formula_report_passes_when_required_fields_present():
    params: dict[str, object] = dict(V23_PARAMS)
    params["v10"] = {
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
    report = build_apex_formula_report(params)
    assert report["schema"] == "ApexRuntimeOSFormulaReport/v1"
    assert report["status"] == "PASS"
    assert report["missing_v2_3_fields"] == []
    assert report["missing_v10_fields"] == []
    assert report["side_effects"] == "read_only_report"


def test_formula_report_warns_without_live_numeric_telemetry():
    report = build_apex_formula_report({})
    assert report["status"] == "WARN"
    assert report["missing_v2_3_fields"] == list(STANDARD_V23_FIELDS)
    assert report["missing_v10_fields"] == list(V10_FINAL_FIELDS)
    assert report["boundary"].startswith("APEX v2.3 is executable")


def test_formula_report_from_runtimeos_status_is_read_only():
    report = build_formula_report_from_runtimeos_status({"schema": "ApexRuntimeOSAutonomyStatus/v1"})
    assert report["schema"] == "ApexRuntimeOSFormulaReport/v1"
    assert report["status"] == "WARN"
    assert report["side_effects"] == "read_only_report"
