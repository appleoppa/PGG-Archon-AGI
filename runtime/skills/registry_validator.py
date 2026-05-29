"""Read-only validators for APEX RuntimeOS skill registry policy.

The registry is a control-plane artifact, not a loader.  These helpers validate
that archived desktop/external evolution materials remain reference-only unless
a separate manifest, sandbox, tests, and explicit promotion path are added.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

_DEFAULT_REGISTRY = Path(__file__).with_name("registry.yaml")
_HIGH_RISK_SOURCE_HINTS = (
    "/desktop/超级进化",
    "desktop/超级进化",
    "external/",
    "github-evolution",
    "super-evolution-core",
    "z-dashen",
)


class SkillRegistryPolicyError(ValueError):
    """Raised when the RuntimeOS skill registry violates safety policy."""


def load_skill_registry(path: Path | None = None) -> Dict[str, Any]:
    """Load the skill registry YAML as a mapping."""
    resolved = path or _DEFAULT_REGISTRY
    data = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SkillRegistryPolicyError("skill registry must be a mapping")
    return data


def _entries(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _is_high_risk_source(source: Any) -> bool:
    text = str(source or "").lower()
    return any(hint.lower() in text for hint in _HIGH_RISK_SOURCE_HINTS)


def validate_skill_registry_policy(registry: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Validate deny-by-default and archived-material read-only policy.

    The report is aggregate-only and side-effect free.  It does not import,
    execute, install, or trust any external/desktop material.
    """
    data = registry if registry is not None else load_skill_registry()
    violations: list[Dict[str, str]] = []
    policy = str(data.get("policy") or "")
    if policy != "deny_by_default":
        violations.append({"code": "registry_policy_not_deny_by_default", "field": "policy"})

    high_risk_reference_ids: list[str] = []
    for bucket_name in ("trusted", "sandboxed", "candidate", "reference_only"):
        for entry in _entries(data.get(bucket_name)):
            source = entry.get("source")
            entry_id = str(entry.get("id") or "unknown")
            status = str(entry.get("status") or "")
            high_risk = _is_high_risk_source(source)
            if high_risk and bucket_name != "reference_only":
                violations.append({"code": "high_risk_source_not_reference_only", "id": entry_id, "bucket": bucket_name})
            if high_risk and status != "reference_only":
                violations.append({"code": "high_risk_source_status_not_reference_only", "id": entry_id, "status": status})
            if bucket_name == "reference_only" and high_risk:
                high_risk_reference_ids.append(entry_id)

    return {
        "schema": "ApexRuntimeOSSkillRegistryPolicyReport/v1",
        "status": "PASS" if not violations else "BLOCK",
        "policy": policy,
        "reference_only_high_risk_count": len(sorted(set(high_risk_reference_ids))),
        "reference_only_high_risk_ids": sorted(set(high_risk_reference_ids)),
        "violations": violations,
        "side_effects": "read_only_report",
        "boundary": "Registry validation only checks policy metadata; it does not execute, import, trust, or install archived materials.",
    }


__all__ = [
    "SkillRegistryPolicyError",
    "load_skill_registry",
    "validate_skill_registry_policy",
]
