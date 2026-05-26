"""APEX RuntimeOS CMMI-style quality gate runner.

The runner evaluates evidence presence only.  It does not run tests, publish,
modify files, or approve releases by itself.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

_DEFAULT_GATE = Path(__file__).with_name("cmmi_gate.yaml")


class QualityGateError(ValueError):
    """Raised when the quality gate definition is invalid."""


def load_quality_gate(path: Path | None = None) -> Dict[str, Any]:
    resolved = path or _DEFAULT_GATE
    data = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise QualityGateError("quality gate must be a mapping")
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise QualityGateError("quality gate rules must be a list")
    return data


def evaluate_quality_gate(evidence: Mapping[str, Any], *, gate_path: Path | None = None) -> Dict[str, Any]:
    gate = load_quality_gate(gate_path)
    results = []
    blocking_failed = 0
    warning_failed = 0
    for raw_rule in gate.get("rules", []):
        if not isinstance(raw_rule, Mapping):
            raise QualityGateError("each quality gate rule must be a mapping")
        rule_id = str(raw_rule.get("id") or "")
        severity = str(raw_rule.get("severity") or "warning")
        required = str(raw_rule.get("required_evidence") or rule_id)
        present = bool(evidence.get(required))
        if not present and severity == "blocking":
            blocking_failed += 1
        elif not present:
            warning_failed += 1
        results.append({
            "id": rule_id,
            "severity": severity,
            "required_evidence": required,
            "passed": present,
        })
    status = "PASS" if blocking_failed == 0 else "BLOCK"
    if status == "PASS" and warning_failed:
        status = "WARN"
    return {
        "schema": "ApexRuntimeOSQualityGateReport/v1",
        "status": status,
        "blocking_failed": blocking_failed,
        "warning_failed": warning_failed,
        "results": results,
        "evidence_summary": {str(key): bool(value) for key, value in evidence.items()},
        "side_effects": "read_only_report",
    }


def build_quality_gate_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a read-only CMMI quality gate report from aggregate RuntimeOS status.

    The mapping is intentionally conservative. RuntimeOS can prove that the
    gate definition exists and that autonomy writes are deny-by-default, but it
    cannot infer that the current change has a test report, audit log, or docs
    unless those evidence flags are provided explicitly by the caller.
    """
    raw_supplied = status.get("quality_evidence")
    supplied: Mapping[str, Any] = raw_supplied if isinstance(raw_supplied, Mapping) else {}
    raw_cron = status.get("cron_dryrun")
    cron: Mapping[str, Any] = raw_cron if isinstance(raw_cron, Mapping) else {}
    evidence = {
        "requirements": True,
        "rollback_plan": status.get("default_side_effects") == "disabled_unless_explicit_enforce",
        "security_review": status.get("default_side_effects") == "disabled_unless_explicit_enforce",
        "audit_log": bool(status.get("promotion_audit_exists") or cron.get("ledger_exists")),
        "test_report": False,
        "documentation": False,
    }
    for key in ("requirements", "rollback_plan", "test_report", "security_review", "audit_log", "documentation"):
        if key in supplied:
            evidence[key] = bool(supplied.get(key))
    report = evaluate_quality_gate(evidence)
    report["evidence_summary"] = {key: bool(value) for key, value in evidence.items()}
    report["boundary"] = "CMMI gate is read-only visibility; it does not run tests or approve releases."
    return report


__all__ = ["QualityGateError", "evaluate_quality_gate", "load_quality_gate", "build_quality_gate_from_runtimeos_status"]
