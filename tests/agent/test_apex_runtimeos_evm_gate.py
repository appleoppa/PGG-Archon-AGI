import pytest

from agent.apex_runtimeos_evm_gate import (
    DEFECT_CODES,
    build_evm_gate_from_runtimeos_status,
    build_evm_gate_report,
    infer_defects_from_runtimeos_status,
    normalize_defects,
)


def test_normalize_defects_completes_twelve_vector():
    defects = normalize_defects({"Err": 0.2, "Mem": 0.1})
    assert set(defects) == set(DEFECT_CODES)
    assert defects["Err"] == 0.2
    assert defects["Mem"] == 0.1
    assert defects["Tok"] == 0.0


def test_normalize_defects_rejects_unknown_or_out_of_range():
    with pytest.raises(ValueError, match="unknown EVM defect"):
        normalize_defects({"BAD": 0.1})
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        normalize_defects({"Err": 1.2})
    with pytest.raises(TypeError, match="numeric"):
        normalize_defects({"Err": "high"})


def test_evm_gate_report_passes_when_low_defect_and_evidence_present():
    report = build_evm_gate_report(
        {"Err": 0.05},
        trace_written=True,
        memory_persisted=True,
        validation_passed=True,
    )
    assert report["schema"] == "ApexRuntimeOSEVMGate/v1"
    assert report["status"] == "PASS"
    assert report["evm_value"] >= 0.75
    assert report["missing_completion_evidence"] == []
    assert report["side_effects"] == "read_only_report"


def test_evm_gate_blocks_high_residual_defect():
    report = build_evm_gate_report({code: 1.0 for code in DEFECT_CODES}, trace_written=True, validation_passed=True)
    assert report["status"] == "BLOCK"
    assert report["evm_value"] < 0.60


def test_evm_gate_warns_when_evidence_missing_even_if_score_high():
    report = build_evm_gate_report({"Err": 0.0})
    assert report["status"] == "WARN"
    assert "trace_written" in report["missing_completion_evidence"]
    assert "validation_passed" in report["missing_completion_evidence"]
    assert "memory_persisted_or_marked_temporary" in report["missing_completion_evidence"]


def test_evm_gate_reduction_uses_after_vector():
    report = build_evm_gate_report({"Err": 0.8}, after_defects={"Err": 0.2}, trace_written=True, validation_passed=True)
    assert report["governance_reduction"] > 0
    assert report["raw_defect_rate"] > report["governed_defect_rate"]


def test_infer_defects_from_runtimeos_status_uses_aggregate_only_fields():
    status = {
        "pending_rollbacks": 2,
        "stable_ready_count": 4,
        "cron_dryrun": {"bad_lines": 3},
        "health_report": {"alert_count": 1},
    }
    defects = infer_defects_from_runtimeos_status(status)
    assert defects["Log"] > 0
    assert defects["Run"] > 0
    assert defects["Err"] > 0
    assert defects["Mem"] > 0
    assert defects["Res"] > 0


def test_build_evm_gate_from_runtimeos_status_is_read_only_report():
    report = build_evm_gate_from_runtimeos_status({"cron_dryrun": {"bad_lines": 0}, "health_report": {"alert_count": 0}})
    assert report["trace_written"] is True
    assert report["validation_passed"] is True
    assert report["memory_persisted"] is False
    assert report["side_effects"] == "read_only_report"
    assert report["boundary"].startswith("EVM means APEX RuntimeOS")
