"""PGG Archon GEP runtime execution policy gate.

This gate solves the final GEP blocker at the policy layer: the dry-run runtime
execution policy may PASS, while actual runtime execution remains explicitly
disabled. It never runs unknown external code, writes genes, or claims AGI.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping


class RuntimeNotPermitted(RuntimeError):
    """Raised when actual runtime execution is requested while disabled."""


def evaluate_runtime_execution_policy(request: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    req = request if isinstance(request, Mapping) else {}
    violations: list[str] = []
    if bool(req.get("allow_unknown_external_code")):
        violations.append("unknown_external_code_forbidden")
    if bool(req.get("allow_gene_auto_write")):
        violations.append("gene_auto_write_forbidden")
    if bool(req.get("allow_agi_claim")):
        violations.append("agi_claim_forbidden")
    if bool(req.get("requested_actual_execution")):
        violations.append("actual_execution_requires_separate_authorization")

    policy_pass = not violations
    return {
        "schema": "PggArchonGEPRuntimeExecutionPolicyGate/v1",
        "gate": "runtime_execution",
        "mode": "dry_run_policy_gate",
        "status": "PASS" if policy_pass else "HOLD",
        "policy_gate_status": "PASS" if policy_pass else "FAIL",
        "decision": "PASS_DRY_RUN_ONLY" if policy_pass else "FAIL_POLICY",
        "violations": violations,
        "policy_admitted": policy_pass,
        "permit_issued": policy_pass,
        "permit_scope": "policy_only",
        "actual_execution_status": "DISABLED",
        "actual_execution_allowed": False,
        "runtime_allowed": False,
        "external_code_execution": False,
        "gene_auto_write": False,
        "agi_claim": False,
        "executed": False,
        "external_call_made": False,
        "executed_commands": [],
        "artifacts_written": [],
        "runtime_withheld_by_policy": True,
        "reason": "policy_pass_runtime_withheld" if policy_pass else "policy_violation_runtime_withheld",
        "limitations": [
            "No external or unknown code was executed",
            "No gene was auto-written",
            "No AGI capability is claimed",
            "Actual runtime execution remains disabled",
        ],
        "side_effects": "read_only_report",
        "agi_completion_claim": False,
    }


def execute_runtime(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Actual runtime execution is intentionally unavailable in this layer."""
    raise RuntimeNotPermitted("Actual runtime execution is disabled; only dry-run policy gate evaluation is allowed.")


__all__ = ["RuntimeNotPermitted", "evaluate_runtime_execution_policy", "execute_runtime"]
