from __future__ import annotations

import pytest

from agent.apex_runtimeos_sequence import (
    REQUIRED_SEQUENCE_ORDER,
    SequenceValidationError,
    build_cycle_state_report,
    build_sequence_gate_from_runtimeos_status,
    build_sequence_gate_report,
    normalize_sequence_code,
)


def _valid_records():
    return [
        {"sequence": "21354", "evidence": True, "output": True, "score": 0.8, "shortcoming": "audit gap"},
        {"sequence": "12534", "evidence": True, "output": True, "score": 0.9, "shortcoming": "fusion gap"},
        {"sequence": "14325", "evidence": True, "output": True, "score": 0.85, "shortcoming": "counter gap"},
    ]


def test_sequence_code_normalization_rejects_unknown():
    assert normalize_sequence_code("21354") == "21354"
    with pytest.raises(SequenceValidationError):
        normalize_sequence_code("spex")


def test_sequence_gate_passes_complete_three_sequence_evidence():
    report = build_sequence_gate_report(_valid_records())
    assert report["schema"] == "ApexRuntimeOSSequenceGate/v1"
    assert report["status"] == "PASS"
    assert report["required_order"] == list(REQUIRED_SEQUENCE_ORDER)
    assert report["observed_order"] == ["21354", "12534", "14325"]
    assert report["complete"] is True
    assert report["side_effects"] == "read_only_report"


def test_sequence_gate_blocks_empty_evidence_instead_of_fake_pass():
    report = build_sequence_gate_report([])
    assert report["status"] == "BLOCK"
    assert report["missing_sequences"] == ["21354", "12534", "14325"]
    assert {item["code"] for item in report["issues"]} == {"missing_sequence"}


def test_sequence_gate_warns_partial_and_missing_shortcoming():
    report = build_sequence_gate_report([
        {"sequence": "21354", "evidence": True, "output": True, "score": 0.7},
        {"sequence": "12534", "evidence": True, "output": True, "score": 0.7, "shortcoming": "fusion gap"},
    ])
    assert report["status"] == "WARN"
    assert "14325" in report["missing_sequences"]
    assert {item["code"] for item in report["issues"]} >= {"missing_shortcoming", "missing_sequence"}


def test_sequence_gate_rejects_malformed_and_duplicate_records():
    report = build_sequence_gate_report([
        {"sequence": "21354", "evidence": True, "output": True, "shortcoming": "a"},
        {"sequence": "21354", "evidence": True, "output": True, "shortcoming": "b"},
        {"sequence": "bad", "evidence": True},
    ])
    codes = [item["code"] for item in report["issues"]]
    assert "duplicate_sequence" in codes
    assert "malformed_record" in codes


def test_cycle_state_report_passes_5_rounds_2_loops_3_sequences():
    cycle = {
        "rounds": [
            {"round": ridx + 1, "loops": [{"sequences": list(REQUIRED_SEQUENCE_ORDER)}, {"sequences": list(REQUIRED_SEQUENCE_ORDER)}]}
            for ridx in range(5)
        ]
    }
    report = build_cycle_state_report(cycle)
    assert report["schema"] == "ApexRuntimeOSCycleState/v1"
    assert report["status"] == "PASS"
    assert report["round_count"] == 5
    assert report["issues"] == []


def test_cycle_state_report_warns_incomplete_cycle():
    report = build_cycle_state_report({"rounds": [{"loops": [{"sequences": ["21354"]}]}]})
    assert report["status"] == "WARN"
    assert {item["code"] for item in report["issues"]} >= {
        "round_count_mismatch",
        "loop_count_mismatch",
        "sequence_gate_failed",
    }


def test_sequence_gate_from_runtimeos_status_defaults_to_block_without_evidence():
    report = build_sequence_gate_from_runtimeos_status({"schema": "ApexRuntimeOSAutonomyStatus/v1"})
    assert report["status"] == "BLOCK"
    assert report["side_effects"] == "read_only_report"
