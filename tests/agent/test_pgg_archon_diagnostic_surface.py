"""Tests for PGG Archon Diagnostic Surface."""

from __future__ import annotations

from agent.pgg_archon_diagnostic_surface import (
    SURFACE_SOURCE,
    SURFACE_VERSION,
    SubsystemHealth,
    SystemHealthReport,
    build_pgg_archon_diagnostic_surface,
)


def test_all_healthy_returns_pass():
    """All subsystems healthy -> PASS."""
    result = build_pgg_archon_diagnostic_surface([
        {"name": "db", "status": "healthy", "details": "Connected"},
        {"name": "api", "status": "healthy", "details": "Responding"},
        {"name": "cache", "status": "healthy", "details": "Warm"},
    ])
    assert result["schema"] == SURFACE_VERSION
    assert result["source"] == SURFACE_SOURCE
    assert result["status"] == "PASS"
    assert result["overall_status"] == "PASS"
    assert result["total_count"] == 3
    assert result["healthy_count"] == 3
    assert result["degraded_count"] == 0
    assert result["critical_count"] == 0
    assert result["warnings"] == []
    assert result["failures"] == []
    assert result["agi_completion_claim"] is False


def test_mixed_healthy_degraded_returns_watch():
    """Mixed healthy + degraded -> WATCH."""
    result = build_pgg_archon_diagnostic_surface([
        {"name": "db", "status": "healthy"},
        {"name": "api", "status": "degraded", "details": "High latency"},
    ])
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "WATCH"
    assert result["overall_status"] == "WATCH"
    assert result["healthy_count"] == 1
    assert result["degraded_count"] == 1
    assert result["critical_count"] == 0
    assert result["warnings"] == ["DegradedSubsystems"]
    assert result["failures"] == []
    assert result["agi_completion_claim"] is False


def test_mixed_healthy_critical_returns_block():
    """Mixed healthy + critical -> BLOCK."""
    result = build_pgg_archon_diagnostic_surface([
        {"name": "db", "status": "healthy"},
        {"name": "api", "status": "critical", "details": "Down"},
    ])
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "BLOCK"
    assert result["overall_status"] == "BLOCK"
    assert result["healthy_count"] == 1
    assert result["degraded_count"] == 0
    assert result["critical_count"] == 1
    assert result["failures"] == ["CriticalSubsystem:api"]
    assert result["warnings"] == []
    assert result["agi_completion_claim"] is False


def test_empty_subsystems_returns_pass():
    """Empty subsystems list -> PASS (vacuously true)."""
    result = build_pgg_archon_diagnostic_surface([])
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "PASS"
    assert result["overall_status"] == "PASS"
    assert result["total_count"] == 0
    assert result["healthy_count"] == 0
    assert result["warnings"] == []
    assert result["failures"] == []
    assert result["agi_completion_claim"] is False


def test_missing_input_returns_watch():
    """None input -> WATCH + DiagnosticsInputMissing."""
    result = build_pgg_archon_diagnostic_surface(None)
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "WATCH"
    assert result["overall_status"] == "WATCH"
    assert result["warnings"] == ["DiagnosticsInputMissing"]
    assert result["agi_completion_claim"] is False
