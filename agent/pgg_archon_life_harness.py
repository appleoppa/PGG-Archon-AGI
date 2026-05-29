"""
PGG Archon — LifeHarnessSurface/v1

Source: APEX-AGI omega-agi/life_harness/src/*.rs
Absorbed: 2026-05-28

Purpose: Read-only life harness state protocol for the PGG Archon AGI.
         Records heartbeat health, recovery events, and resource usage
         without starting daemons or background monitoring loops.

NOT:
  - Starting background daemons or cron loops
  - Making autonomous recovery decisions
  - Persisting state to disk automatically
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class SystemStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"


class RecoveryAction(Enum):
    NONE = "none"
    RESTART_SUBSYSTEM = "restart_subsystem"
    RESET_TO_LAST_GOOD = "reset_to_last_good"
    FULL_RESTART = "full_restart"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


@dataclass
class HeartbeatSnapshot:
    """Current heartbeat status."""
    last_ping: str  # ISO timestamp or "never"
    consecutive_successes: int
    consecutive_failures: int
    total_pings: int
    healthy: bool
    uptime_secs: int

    def to_dict(self) -> dict:
        return {
            "last_ping": self.last_ping,
            "successes": self.consecutive_successes,
            "failures": self.consecutive_failures,
            "total_pings": self.total_pings,
            "healthy": self.healthy,
            "uptime_secs": self.uptime_secs,
        }


@dataclass
class ResourceSnapshot:
    """Resource usage at a point in time."""
    timestamp: str
    cpu_percent: float
    memory_mb: float
    disk_gb: float
    network_active: bool

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "disk_gb": self.disk_gb,
            "network_active": self.network_active,
            "summary": f"CPU: {self.cpu_percent:.1f}% | MEM: {self.memory_mb:.0f} MB | DISK: {self.disk_gb:.1f} GB",
        }


@dataclass
class RecoveryEntry:
    """A single recovery event."""
    action: str
    reason: str
    count: int
    timestamp: str

    def to_dict(self) -> dict:
        return {"action": self.action, "reason": self.reason, "count": self.count, "timestamp": self.timestamp}


@dataclass
class HealthSummary:
    """Comprehensive system health summary."""
    status: str
    uptime_secs: int
    heartbeat: HeartbeatSnapshot
    resources: Optional[ResourceSnapshot]
    sessions_active: int
    warnings: List[str]
    errors: List[str]
    last_recovery: Optional[RecoveryEntry]
    recovery_count: int

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "uptime_secs": self.uptime_secs,
            "heartbeat": self.heartbeat.to_dict(),
            "resources": self.resources.to_dict() if self.resources else None,
            "sessions_active": self.sessions_active,
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "last_recovery": self.last_recovery.to_dict() if self.last_recovery else None,
            "recovery_count": self.recovery_count,
        }


def compute_status(hb: HeartbeatSnapshot, errors: int, warnings: int) -> str:
    """Derive system status from heartbeat and error state."""
    if errors > 0:
        return SystemStatus.CRITICAL.value
    if hb.consecutive_failures > 0 or warnings > 0:
        return SystemStatus.DEGRADED.value
    return SystemStatus.HEALTHY.value


# ── reporters (stateless observation functions) ──


def make_heartbeat(
    successes: int = 0,
    failures: int = 0,
    max_failures: int = 3,
    uptime: int = 0,
) -> HeartbeatSnapshot:
    """Create a heartbeat snapshot from raw counters."""
    return HeartbeatSnapshot(
        last_ping=datetime.utcnow().isoformat(),
        consecutive_successes=successes,
        consecutive_failures=failures,
        total_pings=successes + failures,
        healthy=failures < max_failures,
        uptime_secs=uptime,
    )


def make_health_summary(
    heartbeat: HeartbeatSnapshot,
    resources: Optional[ResourceSnapshot] = None,
    sessions: int = 0,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    last_recovery: Optional[RecoveryEntry] = None,
    recovery_count: int = 0,
) -> HealthSummary:
    """Build a HealthSummary from components."""
    w = warnings or []
    e = errors or []
    return HealthSummary(
        status=compute_status(heartbeat, len(e), len(w)),
        uptime_secs=heartbeat.uptime_secs,
        heartbeat=heartbeat,
        resources=resources,
        sessions_active=sessions,
        warnings=w,
        errors=e,
        last_recovery=last_recovery,
        recovery_count=recovery_count,
    )


def make_recovery_entry(action: str, reason: str, count: int) -> RecoveryEntry:
    """Create a recovery entry."""
    return RecoveryEntry(
        action=action,
        reason=reason,
        count=count,
        timestamp=datetime.utcnow().isoformat(),
    )


SURFACE_VERSION = "PGGArchonLifeHarnessSurface/v1"
SURFACE_SOURCE = "APEX-AGI omega-agi/life_harness/src/*.rs"
SURFACE_ABSORBED = "2026-05-28"
