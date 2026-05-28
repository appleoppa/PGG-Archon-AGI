"""PGG Archon — DiagnosticSurface/v1.

Pure data structures for subsystem health diagnostics, adapted from:
- APEX-AGI hypercore/src/diagnostics.rs
- APEX-AGI hypercore/src/health.rs

This module is read-only: no state, no background monitoring, no model calls,
no gene writes, no daemon starts, no AGI completion claims.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SURFACE_VERSION = "PGGArchonDiagnosticSurface/v1"
SURFACE_SOURCE = "APEX-AGI hypercore/src/diagnostics.rs + hypercore/src/health.rs"


@dataclass(frozen=True)
class SubsystemHealth:
    """A single subsystem's health status."""
    name: str
    status: str  # "healthy", "degraded", or "critical"
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
        }


@dataclass(frozen=True)
class SystemHealthReport:
    """Aggregate system health report."""
    timestamp: str
    overall_status: str  # "PASS", "WATCH", "BLOCK"
    subsystems: list[SubsystemHealth]
    recommendation: str = ""
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "subsystems": [s.to_dict() for s in self.subsystems],
            "recommendation": self.recommendation,
            "uptime_seconds": self.uptime_seconds,
        }


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _health_to_report(
    subsystem_statuses: Sequence[Mapping[str, str]] | None = None,
    *,
    uptime_seconds: float = 0.0,
) -> dict[str, Any]:
    """Convert a list of subsystem status dicts into a structured health report.

    Each entry in subsystem_statuses should have at minimum a 'name' and 'status' key.
    Status values: 'healthy', 'degraded', 'critical'.

    Args:
        subsystem_statuses: Sequence of dicts with name/status/details keys.
        uptime_seconds: Optional uptime in seconds.

    Returns:
        A structured report dict with schema, status, and health details.
    """
    if subsystem_statuses is None:
        return {
            "schema": SURFACE_VERSION,
            "source": SURFACE_SOURCE,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "WATCH",
            "overall_status": "WATCH",
            "subsystems": [],
            "total_count": 0,
            "healthy_count": 0,
            "degraded_count": 0,
            "critical_count": 0,
            "recommendation": "No subsystem statuses supplied; diagnostics cannot be evaluated.",
            "warnings": ["DiagnosticsInputMissing"],
            "failures": [],
            "uptime_seconds": uptime_seconds,
            "agi_completion_claim": False,
        }

    entries = list(_as_sequence(subsystem_statuses))
    subsystems = []
    for item in entries:
        name = str(item.get("name", "unnamed"))
        status = str(item.get("status", "unknown")).lower()
        details = str(item.get("details", ""))
        subsystems.append(SubsystemHealth(name=name, status=status, details=details))

    healthy_count = sum(1 for s in subsystems if s.status == "healthy")
    degraded_count = sum(1 for s in subsystems if s.status == "degraded")
    critical_count = sum(1 for s in subsystems if s.status == "critical")

    # Status logic from the spec:
    # All healthy -> PASS
    # Any critical -> BLOCK
    # Any degraded -> WATCH
    # Empty -> PASS (vacuously true)
    if critical_count > 0:
        overall_status = "BLOCK"
        recommendation = "Critical subsystem failures detected; immediate attention required."
        failures = [f"CriticalSubsystem:{s.name}" for s in subsystems if s.status == "critical"]
        warnings = []
    elif degraded_count > 0:
        overall_status = "WATCH"
        recommendation = "Degraded subsystems detected; review recommended."
        warnings = ["DegradedSubsystems"]
        failures = []
    else:
        overall_status = "PASS"
        recommendation = "All subsystems healthy."
        warnings = []
        failures = []

    report = {
        "schema": SURFACE_VERSION,
        "source": SURFACE_SOURCE,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": overall_status,
        "overall_status": overall_status,
        "subsystems": [s.to_dict() for s in subsystems],
        "total_count": len(subsystems),
        "healthy_count": healthy_count,
        "degraded_count": degraded_count,
        "critical_count": critical_count,
        "recommendation": recommendation,
        "warnings": warnings,
        "failures": failures,
        "uptime_seconds": uptime_seconds,
        "agi_completion_claim": False,
    }
    return report


def build_pgg_archon_diagnostic_surface(
    subsystem_statuses: Sequence[Mapping[str, str]] | None = None,
    *,
    uptime_seconds: float = 0.0,
) -> dict[str, Any]:
    """Build a structured diagnostic surface from caller-supplied subsystem statuses.

    This is a pure function with no side effects. It takes caller-supplied data and
    returns a structured report. No model calls, no gene writes, no daemon starts.

    Args:
        subsystem_statuses: List of dicts, each with 'name', 'status', and optional 'details'.
            Valid statuses: 'healthy', 'degraded', 'critical'.
        uptime_seconds: Optional system uptime in seconds.

    Returns:
        A structured dict with schema, status, subsystem details, and aggregate counts.
    """
    return _health_to_report(subsystem_statuses, uptime_seconds=uptime_seconds)


__all__ = [
    "SURFACE_VERSION",
    "SURFACE_SOURCE",
    "SubsystemHealth",
    "SystemHealthReport",
    "_health_to_report",
    "build_pgg_archon_diagnostic_surface",
]
