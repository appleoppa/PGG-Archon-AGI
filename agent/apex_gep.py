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


def build_gep_safety_pipeline(index: Mapping[str, Any] | None = None, resource_preflight: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Return the read-only safety pipeline required before GEP runtime use.

    The archived Book-to-skill/GitHub/GEP materials describe powerful runtime
    ingestion and validation loops. This helper deliberately turns that into a
    visible HOLD pipeline instead of executing archived JavaScript or treating
    obfuscated code as trusted capability.
    """
    capability_index = index if isinstance(index, Mapping) else build_gep_capability_index()
    counts_raw = capability_index.get("counts") if isinstance(capability_index.get("counts"), Mapping) else {}
    counts: Mapping[str, Any] = counts_raw if isinstance(counts_raw, Mapping) else {}
    obfuscated_count = int(counts.get("archived_obfuscated") or 0)
    missing_count = int(counts.get("missing") or 0)
    preflight = resource_preflight if isinstance(resource_preflight, Mapping) else {}
    preflight_pass = str(preflight.get("status") or "").upper() == "PASS"
    resource_index_raw = preflight.get("resource_index")
    resource_index: Mapping[str, Any] = resource_index_raw if isinstance(resource_index_raw, Mapping) else {}
    resource_preflight_stage = {
        "id": "resource_manifest_preflight",
        "status": "PASS" if preflight_pass else "HOLD",
        "substatus": preflight.get("substatus") or "RESOURCE_PRECHECK_MISSING",
        "resource_count": int(preflight.get("resource_count") or 0),
        "index_status": resource_index.get("status"),
        "required_before_runtime": True,
        "side_effects": "read_only_report",
    }
    stages = [
        {
            "id": "component_inventory",
            "status": "PASS" if capability_index.get("component_count") else "BLOCK",
            "side_effects": "read_only_report",
        },
        {
            "id": "deobfuscation_review",
            "status": "HOLD" if obfuscated_count else "PASS",
            "required_before_runtime": True,
            "obfuscated_count": obfuscated_count,
        },
        {
            "id": "missing_component_review",
            "status": "BLOCK" if missing_count else "PASS",
            "missing_count": missing_count,
        },
        resource_preflight_stage,
        {
            "id": "sandbox_validator_bridge",
            "status": "HOLD",
            "required_before_runtime": True,
            "required_guards": ["feature_flag", "preflight", "sandbox", "tasks_only", "max_tasks_per_cycle"],
        },
        {
            "id": "external_ingestion_review",
            "status": "HOLD",
            "required_before_runtime": True,
            "surfaces": ["book_to_skill", "github_ingestion"],
            "required_guards": [
                "source_manifest",
                "license_review",
                "checksum_or_hash",
                "read_only_parser",
                "no_unknown_code_execution",
                "quality_evidence_bundle",
            ],
            "reason": "Book-to-skill and GitHub ingestion stay as read-only metadata pipelines until provenance, license, checksum, tests, and quality evidence are present.",
        },
        {
            "id": "runtime_execution",
            "status": "HOLD",
            "allowed_now": False,
            "reason": "archived_or_external_code_and_generated_skills_must_remain_read_only_until_all_prior_stages_pass",
        },
    ]
    if missing_count:
        status = "BLOCK"
    else:
        status = "HOLD"
    return {
        "schema": "ApexRuntimeOSGEPSafetyPipeline/v1",
        "status": status,
        "runtime_allowed": False,
        "stages": stages,
        "hold_reasons": [stage["id"] for stage in stages if stage.get("status") in {"HOLD", "BLOCK"}],
        "boundary": "Read-only gate only; no external repositories, archived JavaScript, validators, books, GitHub ingestion, or generated skills are executed.",
        "side_effects": "read_only_report",
    }


def build_gep_report_from_runtimeos_status(status: Mapping[str, Any]) -> Dict[str, Any]:
    from agent.apex_gep_resources import build_gep_resource_preflight_report

    index = build_gep_capability_index()
    resource_preflight = build_gep_resource_preflight_report()
    return {
        "schema": "ApexRuntimeOSGEPReport/v1",
        "status": index["status"],
        "substatus": resource_preflight["substatus"],
        "capability_index": index,
        "resource_preflight": resource_preflight,
        "safety_pipeline": build_gep_safety_pipeline(index, resource_preflight),
        "question_gate": build_question_gate_report([]),
        "validator_gate": build_validator_gate_report({}),
        "external_code_execution": False,
        "auto_gene_promotion": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


__all__ = [
    "GEP_COMPONENTS",
    "REQUIRED_GEP_COMPONENTS",
    "build_gep_capability_index",
    "build_gep_report_from_runtimeos_status",
    "build_gep_safety_pipeline",
    "build_question_gate_report",
    "build_validator_gate_report",
    "is_infra_question_context",
]
