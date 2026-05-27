from __future__ import annotations

import pytest

from agent.apex_gep_runtime_execution import (
    RuntimeNotPermitted,
    evaluate_runtime_execution_policy,
    execute_runtime,
)


def test_runtime_policy_gate_passes_dry_run_only_without_execution():
    result = evaluate_runtime_execution_policy()
    assert result["schema"] == "PggArchonGEPRuntimeExecutionPolicyGate/v1"
    assert result["gate"] == "runtime_execution"
    assert result["mode"] == "dry_run_policy_gate"
    assert result["status"] == "PASS"
    assert result["policy_gate_status"] == "PASS"
    assert result["decision"] == "PASS_DRY_RUN_ONLY"
    assert result["actual_execution_status"] == "DISABLED"
    assert result["actual_execution_allowed"] is False
    assert result["runtime_allowed"] is False
    assert result["executed"] is False
    assert result["external_call_made"] is False
    assert result["executed_commands"] == []
    assert result["artifacts_written"] == []
    assert result["runtime_withheld_by_policy"] is True
    assert result["agi_completion_claim"] is False


def test_runtime_policy_blocks_unknown_external_code_request():
    result = evaluate_runtime_execution_policy({"allow_unknown_external_code": True})
    assert result["status"] == "HOLD"
    assert result["policy_gate_status"] == "FAIL"
    assert result["decision"] == "FAIL_POLICY"
    assert "unknown_external_code_forbidden" in result["violations"]
    assert result["actual_execution_status"] == "DISABLED"
    assert result["runtime_allowed"] is False


def test_runtime_policy_blocks_gene_auto_write_and_agi_claim():
    result = evaluate_runtime_execution_policy({"allow_gene_auto_write": True, "allow_agi_claim": True})
    assert result["status"] == "HOLD"
    assert "gene_auto_write_forbidden" in result["violations"]
    assert "agi_claim_forbidden" in result["violations"]
    assert result["gene_auto_write"] is False
    assert result["agi_claim"] is False


def test_runtime_policy_blocks_actual_execution_request():
    result = evaluate_runtime_execution_policy({"requested_actual_execution": True})
    assert result["status"] == "HOLD"
    assert "actual_execution_requires_separate_authorization" in result["violations"]
    assert result["actual_execution_allowed"] is False
    assert result["executed_commands"] == []


def test_execute_runtime_is_hard_disabled():
    with pytest.raises(RuntimeNotPermitted):
        execute_runtime()
