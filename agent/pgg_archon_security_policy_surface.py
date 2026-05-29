"""PGG Archon — SecurityPolicySurface/v1.

Pure data structures for security ring-based capability access control, adapted from:
- APEX-AGI hypercore/src/security.rs

This module is read-only: no mutable state, no background threads, no model calls,
no gene writes, no daemon starts, no AGI completion claims.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping, Sequence

SURFACE_VERSION = "PGGArchonSecurityPolicySurface/v1"
SURFACE_SOURCE = "APEX-AGI hypercore/src/security.rs"


class SecurityRing(IntEnum):
    """Security rings from most privileged to least."""
    Kernel = 0
    Hypervisor = 1
    Supervisor = 2
    User = 3


@dataclass(frozen=True)
class Capability:
    """A security capability tied to a minimum ring level."""
    id: str
    description: str
    min_ring: int
    scope: str = ""

    def accessible_by(self, ring: int) -> bool:
        """Returns True if the given ring level can access this capability.

        Lower ring numbers = higher privilege. A capability is accessible if
        the caller's ring <= the capability's minimum required ring.
        """
        return ring <= self.min_ring

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "min_ring": self.min_ring,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class CapabilitySet:
    """An immutable set of capabilities."""
    capabilities: list[Capability] = field(default_factory=list)

    def has(self, capability_id: str) -> bool:
        """Check if a capability exists in the set by ID."""
        return any(c.id == capability_id for c in self.capabilities)

    def check(self, capability_id: str, ring: int) -> bool:
        """Check if a capability is both present and accessible from the given ring."""
        for c in self.capabilities:
            if c.id == capability_id:
                return c.accessible_by(ring)
        return False

    def by_scope(self, prefix: str) -> CapabilitySet:
        """Filter capabilities by scope prefix (case-sensitive)."""
        matching = [c for c in self.capabilities if c.scope.startswith(prefix)]
        return CapabilitySet(capabilities=matching)

    def merge(self, other: CapabilitySet) -> CapabilitySet:
        """Merge two capability sets (deduplicates by ID, keeping first occurrence)."""
        existing_ids = {c.id for c in self.capabilities}
        merged = list(self.capabilities)
        for c in other.capabilities:
            if c.id not in existing_ids:
                merged.append(c)
                existing_ids.add(c.id)
        return CapabilitySet(capabilities=merged)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.capabilities]


@dataclass(frozen=True)
class SecurityContext:
    """A security context with ring level, capabilities, and sandbox status."""
    ring: int
    capabilities: CapabilitySet = field(default_factory=CapabilitySet)
    sandboxed: bool = True

    def can(self, capability_id: str) -> bool:
        """Check if this context can access a capability by ID."""
        return self.capabilities.check(capability_id, self.ring)


def _ring_name(ring: int) -> str:
    """Get human-readable name for a ring level."""
    try:
        return SecurityRing(ring).name
    except ValueError:
        return f"Unknown({ring})"


def build_pgg_archon_security_policy_surface(
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured security policy surface from a caller-supplied context dict.

    This is a pure function with no side effects. It validates the security context
    structure and returns a deterministic report.

    Expected context keys:
        - ring (int): Security ring level (0=Kernel, 1=Hypervisor, 2=Supervisor, 3=User)
        - capabilities (list[dict], optional): List of capabilities with id/description/min_ring/scope
        - sandboxed (bool, optional): Whether the context is sandboxed (default: True)

    Args:
        context: Dict describing the security context, or None.

    Returns:
        A structured report dict with schema, status, ring info, capability count, etc.
    """
    if context is None:
        return {
            "schema": SURFACE_VERSION,
            "source": SURFACE_SOURCE,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "WATCH",
            "ring": None,
            "ring_name": "Unknown",
            "sandboxed": None,
            "capability_count": 0,
            "warnings": ["SecurityContextMissing"],
            "failures": [],
            "agi_completion_claim": False,
            "boundary": "No security context was supplied; this is a non-blocking WATCH surface.",
        }

    ctx = dict(context)
    ring = int(ctx.get("ring", 3))
    sandboxed = bool(ctx.get("sandboxed", True))
    raw_caps = ctx.get("capabilities", [])

    if isinstance(raw_caps, list):
        capabilities = CapabilitySet(capabilities=[
            Capability(
                id=str(c.get("id", "")),
                description=str(c.get("description", "")),
                min_ring=int(c.get("min_ring", 3)),
                scope=str(c.get("scope", "")),
            )
            for c in raw_caps
        ])
    else:
        capabilities = CapabilitySet()

    # Determine status
    if ring == SecurityRing.Kernel and not sandboxed:
        status = "PASS"
        warnings = []
        failures = []
    elif ring == SecurityRing.User and sandboxed:
        status = "PASS"
        warnings = []
        failures = []
    else:
        status = "WATCH"
        warnings = ["UnusualSecurityContext:ring={} sandboxed={}".format(ring, sandboxed)]
        failures = []

    report = {
        "schema": SURFACE_VERSION,
        "source": SURFACE_SOURCE,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "ring": ring,
        "ring_name": _ring_name(ring),
        "sandboxed": sandboxed,
        "capability_count": len(capabilities.capabilities),
        "capabilities": capabilities.to_dicts(),
        "warnings": warnings,
        "failures": failures,
        "agi_completion_claim": False,
        "boundary": "Read-only security policy surface. No model calls, no gene writes, no daemon starts.",
    }
    return report


__all__ = [
    "SURFACE_VERSION",
    "SURFACE_SOURCE",
    "SecurityRing",
    "Capability",
    "CapabilitySet",
    "SecurityContext",
    "build_pgg_archon_security_policy_surface",
]
