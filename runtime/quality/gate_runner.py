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
        "side_effects": "read_only_report",
    }


__all__ = ["QualityGateError", "evaluate_quality_gate", "load_quality_gate"]
