"""APEX RuntimeOS read-only Evolver GEP gate.

This module extracts a safe capability index from the archived Evolver GEP
source tree.  It does not execute the JavaScript implementation, contact hubs,
write assets, mutate memory graphs, or run validators.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Mapping, Sequence

GEP_COMPONENTS: Dict[str, Dict[str, Any]] = {
    "memoryGraph": {
        "source": "external/super-evolution-core/evolver-main/src/gep/memoryGraph.js",
        "role": "graph_memory",
        "status": "archived_obfuscated",
        "risk": "do_not_execute_until_deobfuscated",
        "required_for_runtime": True,
    },
    "narrativeMemory": {
        "source": "external/super-evolution-core/evolver-main/src/gep/narrativeMemory.js",
        "role": "narrative_memory",
        "status": "archived_obfuscated",
        "risk": "do_not_execute_until_deobfuscated",
        "required_for_runtime": True,
    },
    "questionGenerator": {
        "source": "external/super-evolution-core/evolver-main/src/gep/questionGenerator.js",
        "role": "question_generation",
        "status": "readable_archived",
        "strategies": [
            "recurring_error",
            "capability_gap",
            "evolution_saturation",
            "failure_streak",
            "user_feature_request",
            "perf_bottleneck",
            "hub_search_miss",
            "repair_loop",
            "plateau_pivot",
        ],
        "rate_limits": {"standard_minutes": 30, "urgent_minutes": 5, "max_questions": 3, "max_urgent_questions": 2},
        "required_for_runtime": True,
    },
    "solidify": {
        "source": "external/super-evolution-core/evolver-main/src/gep/solidify.js",
        "role": "gene_capsule_solidification",
        "status": "archived_obfuscated",
        "risk": "do_not_execute_until_deobfuscated",
        "required_for_runtime": True,
    },
    "validator": {
        "source": "external/super-evolution-core/evolver-main/src/gep/validator/index.js",
        "role": "sandbox_validation",
        "status": "readable_archived",
        "feature_gate": "EVOLVER_VALIDATOR_ENABLED",
        "safe_guards": ["feature_flag", "preflight", "sandbox", "max_tasks_per_cycle", "tasks_only_no_charge_fetch"],
        "required_for_runtime": True,
    },
}

REQUIRED_GEP_COMPONENTS = tuple(GEP_COMPONENTS.keys())

QUESTION_INFRA_HINTS = (
    "401", "403", "429", "500", "502", "503", "504", "529",
    "invalid api key", "authentication error", "unauthorized", "permission denied",
    "rate limit", "too many requests", "overloaded", "network error",
    "connection refused", "context length", "token limit",
)


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def is_infra_question_context(text: Any) -> bool:
    lowered = str(text or "").lower()
    return any(hint in lowered for hint in QUESTION_INFRA_HINTS)


def build_gep_capability_index(components: Mapping[str, Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    """Return a redaction-safe GEP component capability index."""
    source = components or GEP_COMPONENTS
    indexed = []
    issues: list[Dict[str, Any]] = []
    counts = {"readable_archived": 0, "archived_obfuscated": 0, "missing": 0}
    for name in REQUIRED_GEP_COMPONENTS:
        raw = source.get(name)
        if not isinstance(raw, Mapping):
            counts["missing"] += 1
            issues.append({"code": "missing_component", "component": name})
            continue
        status = str(raw.get("status") or "missing")
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
        if status == "archived_obfuscated":
            issues.append({"code": "component_obfuscated", "component": name, "risk": raw.get("risk")})
        indexed.append({
            "name": name,
            "role": raw.get("role"),
            "status": status,
            "source_hash": _stable_hash(str(raw.get("source") or name)),
            "required_for_runtime": bool(raw.get("required_for_runtime")),
        })
    if counts.get("missing", 0):
        gate_status = "BLOCK"
    elif counts.get("archived_obfuscated", 0):
        gate_status = "WARN"
    else:
        gate_status = "PASS"
    return {
        "schema": "ApexRuntimeOSGEPCapabilityIndex/v1",
        "status": gate_status,
        "component_count": len(indexed),
        "counts": counts,
        "components": indexed,
        "issues": issues,
        "boundary": "Archived GEP sources are indexed only; JavaScript is not executed and obfuscated modules are not treated as understood runtime capability.",
        "side_effects": "read_only_report",
    }


def build_question_gate_report(candidates: Sequence[Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    """Validate generated question candidates without sending them anywhere."""
    items = list(candidates or [])
    issues: list[Dict[str, Any]] = []
    accepted = []
    seen: set[str] = set()
    for idx, raw in enumerate(items):
        if not isinstance(raw, Mapping):
            issues.append({"code": "malformed_question", "index": idx})
            continue
        question = str(raw.get("question") or "").strip()
        priority = raw.get("priority", 1)
        signals = raw.get("signals") if isinstance(raw.get("signals"), list) else []
        qkey = question.lower()
        if not question:
            issues.append({"code": "missing_question", "index": idx})
            continue
        if qkey in seen:
            issues.append({"code": "duplicate_question", "index": idx})
            continue
        seen.add(qkey)
        if is_infra_question_context(question):
            issues.append({"code": "infra_question_suppressed", "index": idx})
            continue
        if not isinstance(priority, int) or priority < 1 or priority > 3:
            issues.append({"code": "invalid_priority", "index": idx})
            continue
        if not signals or not all(_has_text(item) for item in signals):
            issues.append({"code": "missing_signals", "index": idx})
            continue
        accepted.append({"question_hash": _stable_hash(question), "priority": priority, "signal_count": len(signals)})
    status = "PASS" if accepted and not issues else ("WARN" if accepted else "BLOCK")
    return {
        "schema": "ApexRuntimeOSGEPQuestionGate/v1",
        "status": status,
        "candidate_count": len(items),
        "accepted_count": len(accepted),
        "accepted": accepted,
        "issues": issues,
        "side_effects": "read_only_report",
    }


def build_validator_gate_report(config: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Validate safe preconditions for a future validator bridge."""
    cfg = config or {}
    enabled = bool(cfg.get("enabled", False))
    preflight_ok = bool(cfg.get("preflight_ok", False))
    sandbox_ok = bool(cfg.get("sandbox_ok", False))
    tasks_only = bool(cfg.get("tasks_only", False))
    max_tasks = int(cfg.get("max_tasks_per_cycle") or 0) if isinstance(cfg.get("max_tasks_per_cycle", 0), int) else 0
    issues = []
    if not enabled:
        issues.append({"code": "validator_disabled"})
    if not preflight_ok:
        issues.append({"code": "preflight_missing"})
    if not sandbox_ok:
        issues.append({"code": "sandbox_missing"})
    if not tasks_only:
        issues.append({"code": "tasks_only_guard_missing"})
    if max_tasks < 1 or max_tasks > 10:
        issues.append({"code": "max_tasks_out_of_range"})
    status = "PASS" if not issues else "BLOCK"
    return {
        "schema": "ApexRuntimeOSGEPValidatorGate/v1",
        "status": status,
        "enabled": enabled,
        "preflight_ok": preflight_ok,
        "sandbox_ok": sandbox_ok,
        "tasks_only": tasks_only,
        "max_tasks_per_cycle": max_tasks,
        "issues": issues,
        "side_effects": "read_only_report",
    }


def build_gep_report_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    index = build_gep_capability_index()
    return {
        "schema": "ApexRuntimeOSGEPReport/v1",
        "status": index["status"],
        "capability_index": index,
        "question_gate": build_question_gate_report([]),
        "validator_gate": build_validator_gate_report({}),
        "side_effects": "read_only_report",
    }


__all__ = [
    "GEP_COMPONENTS",
    "REQUIRED_GEP_COMPONENTS",
    "build_gep_capability_index",
    "build_gep_report_from_runtimeos_status",
    "build_question_gate_report",
    "build_validator_gate_report",
    "is_infra_question_context",
]
