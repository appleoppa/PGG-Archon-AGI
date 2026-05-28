"""PGG Archon — QualityGateSurface/v1.

Absorbs the useful CMMI Level 5 quality-gate pattern from:
- APEX-AGI/omega_pipeline/quality_gates.py
- APEX-AGI/omega-agi/engineering/src/quality_gate.rs

This module is intentionally read-only and data-driven. It never compiles code,
runs tests, pushes to git, calls models, writes genes, or starts daemons. It
only evaluates caller-supplied evidence fields and produces a machine-checkable
quality-gate surface for PGG Archon status/review flows.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Mapping, Sequence

SURFACE_VERSION = "PGGArchonQualityGateSurface/v1"
SURFACE_SOURCE = "APEX-AGI omega_pipeline/quality_gates.py + omega-agi/engineering/src/quality_gate.rs"
SURFACE_SOURCE_HASH = hashlib.sha256(SURFACE_SOURCE.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class QualityGateResult:
    gate_name: str
    phase: int
    passed: bool
    severity: str
    details: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QualityGateDefinition:
    gate_name: str
    phase: int
    severity: str
    rationale: str
    check: Callable[[Mapping[str, Any]], tuple[bool, str]]

    def evaluate(self, context: Mapping[str, Any]) -> QualityGateResult:
        try:
            passed, details = self.check(context)
        except Exception as exc:
            passed, details = False, f"gate_error:{type(exc).__name__}"
        return QualityGateResult(
            gate_name=self.gate_name,
            phase=self.phase,
            passed=bool(passed),
            severity=self.severity,
            details=str(details)[:500],
            rationale=self.rationale,
        )


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _hash_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _improvements(context: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [x for x in _as_sequence(context.get("improvements")) if isinstance(x, Mapping)]


def _plan_complete(context: Mapping[str, Any]) -> tuple[bool, str]:
    required = {"id", "param", "file", "tests_added", "phase"}
    improvements = _improvements(context)
    if not improvements:
        return False, "plan_has_no_improvements"
    missing = []
    for i, item in enumerate(improvements):
        miss = sorted(required - set(item.keys()))
        if miss:
            missing.append(f"improvement[{i}] missing {','.join(miss)}")
    return (not missing, "all_improvements_complete" if not missing else "; ".join(missing)[:500])


def _min_improvements(context: Mapping[str, Any]) -> tuple[bool, str]:
    count = len(_improvements(context))
    return count >= 3, f"improvement_count={count} min=3"


def _min_tests(context: Mapping[str, Any]) -> tuple[bool, str]:
    total = sum(_as_int(item.get("tests_added", item.get("tests"))) for item in _improvements(context))
    return total >= 10, f"planned_new_tests={total} min=10"


def _formula_sensitivity(context: Mapping[str, Any]) -> tuple[bool, str]:
    # Requires caller-supplied sensitivity samples, not raw formula execution.
    samples = [_as_float(x) for x in _as_sequence(context.get("formula_sensitivity_samples"))]
    if len(samples) < 2:
        return False, "formula_sensitivity_samples_missing"
    spread = max(samples) - min(samples)
    return spread > 0.01, f"sensitivity_spread={spread:.4f} min=0.01"


def _status_pass(context: Mapping[str, Any], key: str) -> tuple[bool, str]:
    value = str(context.get(key, "")).strip().upper()
    return value == "PASS", f"{key}={value or 'MISSING'}"


def _new_test_count(context: Mapping[str, Any]) -> tuple[bool, str]:
    count = _as_int(context.get("new_tests_added"))
    return count >= 10, f"new_tests_added={count} min=10"


def _no_regression(context: Mapping[str, Any]) -> tuple[bool, str]:
    regressions = _as_int(context.get("regression_count"))
    return regressions == 0, f"regression_count={regressions}"


def _improvement(context: Mapping[str, Any]) -> tuple[bool, str]:
    delta = _as_float(context.get("metric_improvement_delta"))
    return delta > 0, f"metric_improvement_delta={delta:.4f}"


def _commit_message(context: Mapping[str, Any]) -> tuple[bool, str]:
    msg = str(context.get("commit_message") or "").strip()
    ok = 8 <= len(msg) <= 300 and any(prefix in msg.lower() for prefix in ("add", "fix", "bind", "wire", "absorb", "extend", "route", "guard"))
    return ok, f"commit_message_len={len(msg)}"


def default_quality_gates() -> list[QualityGateDefinition]:
    return [
        QualityGateDefinition("PlanCompletenessGate", 1, "blocking", "Every improvement must specify id/param/file/tests_added/phase.", _plan_complete),
        QualityGateDefinition("PlanMinImprovementsGate", 1, "blocking", "Plan should include at least three improvements before claiming a batch.", _min_improvements),
        QualityGateDefinition("PlanMinTestsGate", 1, "blocking", "Planned test additions should be large enough to be meaningful.", _min_tests),
        QualityGateDefinition("FormulaSensitivityGate", 1, "warning", "Formula or score changes need supplied sensitivity evidence.", _formula_sensitivity),
        QualityGateDefinition("CompilationGate", 2, "blocking", "Compilation/syntax status must be PASS.", lambda c: _status_pass(c, "compilation_status")),
        QualityGateDefinition("RustTestGate", 2, "blocking", "Rust test status must be PASS when Rust is touched.", lambda c: _status_pass(c, "rust_test_status")),
        QualityGateDefinition("PythonTestGate", 2, "blocking", "Python test status must be PASS.", lambda c: _status_pass(c, "python_test_status")),
        QualityGateDefinition("NewTestCountGate", 2, "warning", "Execution should add/cover at least ten test cases for a quality batch.", _new_test_count),
        QualityGateDefinition("NoRegressionGate", 3, "blocking", "Regression count must be zero.", _no_regression),
        QualityGateDefinition("ImprovementGate", 3, "warning", "At least one measured metric should improve.", _improvement),
        QualityGateDefinition("FullTestSuiteGate", 3, "warning", "Full/targeted suite status should be PASS.", lambda c: _status_pass(c, "full_test_suite_status")),
        QualityGateDefinition("CommitMessageGate", 3, "warning", "Commit message should be bounded and action-oriented.", _commit_message),
        QualityGateDefinition("GitHubPushGate", 3, "warning", "Push/remote verification status should be PASS.", lambda c: _status_pass(c, "push_status")),
    ]


def build_pgg_archon_quality_gate_surface(context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if context is None:
        report = {
            "schema": SURFACE_VERSION,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "WATCH",
            "source": SURFACE_SOURCE,
            "source_hash": SURFACE_SOURCE_HASH,
            "gate_count": len(default_quality_gates()),
            "passed_count": 0,
            "blocking_failed_count": 0,
            "warning_failed_count": 1,
            "results": [],
            "blocking_failures": [],
            "warning_failures": ["QualityGateContextMissing"],
            "side_effects": "read_only_report",
            "boundary": "No quality-gate context was supplied; this is a non-blocking WATCH surface, not a PASS or promotion claim.",
            "agi_completion_claim": False,
        }
        report["surface_hash"] = _hash_obj(report)
        return report

    ctx = dict(context)
    results = [gate.evaluate(ctx).to_dict() for gate in default_quality_gates()]
    blocking_failed = [r for r in results if r["severity"] == "blocking" and not r["passed"]]
    warnings_failed = [r for r in results if r["severity"] == "warning" and not r["passed"]]
    passed_count = sum(1 for r in results if r["passed"])
    status = "BLOCK" if blocking_failed else ("WATCH" if warnings_failed else "PASS")
    report = {
        "schema": SURFACE_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "source": SURFACE_SOURCE,
        "source_hash": SURFACE_SOURCE_HASH,
        "gate_count": len(results),
        "passed_count": passed_count,
        "blocking_failed_count": len(blocking_failed),
        "warning_failed_count": len(warnings_failed),
        "results": results,
        "blocking_failures": [r["gate_name"] for r in blocking_failed],
        "warning_failures": [r["gate_name"] for r in warnings_failed],
        "side_effects": "read_only_report",
        "boundary": "No compilation, tests, git push, model calls, gene writes, or daemon starts are performed here; only caller-supplied evidence is evaluated.",
        "agi_completion_claim": False,
    }
    report["surface_hash"] = _hash_obj(report)
    return report


__all__ = [
    "SURFACE_VERSION",
    "SURFACE_SOURCE_HASH",
    "QualityGateResult",
    "QualityGateDefinition",
    "default_quality_gates",
    "build_pgg_archon_quality_gate_surface",
]
