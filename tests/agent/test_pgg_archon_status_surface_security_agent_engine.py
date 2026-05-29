"""Status surface integration tests for SecurityPolicySurface and AgentEngineSurface."""

from __future__ import annotations

from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def test_status_surface_includes_security_policy_and_agent_engine_signals():
    result = build_pgg_archon_status_surface(
        security_policy_report={
            "schema": "PGGArchonSecurityPolicySurface/v1",
            "status": "PASS",
            "ring": 3,
            "capability_count": 1,
            "warnings": [],
            "agi_completion_claim": False,
        },
        agent_engine_report={
            "schema": "PGGArchonAgentEngineSurface/v1",
            "status": "PASS",
            "engine_count": 5,
            "warnings": [],
            "agi_completion_claim": False,
        },
    )

    assert result["schema"] == "PGGArchonStatusSurface/v1"
    assert result["signals"]["security_policy_surface_ready"]["ok"] is True
    assert result["signals"]["agent_engine_surface_ready"]["ok"] is True
    assert result["summary"]["security_policy_status"] == "PASS"
    assert result["summary"]["security_policy_schema_ok"] is True
    assert result["summary"]["security_policy_capability_count"] == 1
    assert result["summary"]["agent_engine_status"] == "PASS"
    assert result["summary"]["agent_engine_schema_ok"] is True
    assert result["summary"]["agent_engine_count"] == 5
    assert result["security_policy_surface"]["schema"] == "PGGArchonSecurityPolicySurface/v1"
    assert result["agent_engine_surface"]["schema"] == "PGGArchonAgentEngineSurface/v1"
    assert result["agi_completion_claim"] is False


def test_status_surface_blocks_malformed_security_and_engine_reports():
    result = build_pgg_archon_status_surface(
        security_policy_report={
            "schema": "BadSecuritySchema/v0",
            "status": "PASS",
            "warnings": [],
            "agi_completion_claim": False,
        },
        agent_engine_report={
            "schema": "BadEngineSchema/v0",
            "status": "PASS",
            "warnings": [],
            "agi_completion_claim": False,
        },
    )

    assert result["signals"]["security_policy_surface_ready"]["ok"] is False
    assert result["signals"]["agent_engine_surface_ready"]["ok"] is False
    codes = {item["code"] for item in result["small_bottlenecks"]}
    assert "Sec/Schema" in codes
    assert "Eng/Schema" in codes
    assert result["agi_completion_claim"] is False
