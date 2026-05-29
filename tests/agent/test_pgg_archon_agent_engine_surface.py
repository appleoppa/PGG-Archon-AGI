"""Tests for PGG Archon Agent Engine Surface."""

from __future__ import annotations

from agent.pgg_archon_agent_engine_surface import (
    SURFACE_SOURCE,
    SURFACE_VERSION,
    AgentEngine,
    build_pgg_archon_agent_engine_surface,
)

EXPECTED_ENGINE_NAMES = {
    "react_engine",
    "inference_engine",
    "tool_execution_engine",
    "feedback_engine",
    "knowledge_engine",
}


def test_default_engines_include_all_five():
    """Default engines include all 5 expected engines."""
    result = build_pgg_archon_agent_engine_surface()
    assert result["schema"] == SURFACE_VERSION
    assert result["source"] == SURFACE_SOURCE
    assert result["status"] == "PASS"
    assert result["engine_count"] == 5
    engine_names = set(result["engine_names"])
    assert engine_names == EXPECTED_ENGINE_NAMES
    assert result["agi_completion_claim"] is False


def test_each_engine_has_required_fields():
    """Each engine has name, version, tags, description."""
    result = build_pgg_archon_agent_engine_surface()
    for engine in result["engines"]:
        assert isinstance(engine["name"], str) and engine["name"]
        assert isinstance(engine["version"], str) and engine["version"]
        assert isinstance(engine["capability_tags"], list)
        assert isinstance(engine["description"], str) and engine["description"]
    assert result["agi_completion_claim"] is False


def test_custom_engines_override():
    """Custom engines override works."""
    custom = [
        {"name": "custom_engine_1", "version": "2.0", "capability_tags": ["custom"], "description": "A custom engine"},
        {"name": "custom_engine_2", "version": "1.5", "capability_tags": ["test", "custom"], "description": "Another custom engine"},
    ]
    result = build_pgg_archon_agent_engine_surface(custom_engines=custom)
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "PASS"
    assert result["engine_count"] == 2
    assert result["engine_names"] == ["custom_engine_1", "custom_engine_2"]
    assert result["engines"][0]["version"] == "2.0"
    assert result["engines"][1]["capability_tags"] == ["test", "custom"]
    assert result["agi_completion_claim"] is False


def test_empty_custom_engines_returns_watch():
    """Empty custom engines list -> WATCH status."""
    result = build_pgg_archon_agent_engine_surface(custom_engines=[])
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "WATCH"
    assert result["engine_count"] == 0
    assert result["engine_names"] == []
    assert result["warnings"] == ["NoAgentEnginesDeclared"]
    assert result["agi_completion_claim"] is False


def test_agi_completion_claim_false_on_all_reports():
    """agi_completion_claim=False on all reports — default and custom."""
    # Default
    default = build_pgg_archon_agent_engine_surface()
    assert default["agi_completion_claim"] is False

    # Custom
    custom = build_pgg_archon_agent_engine_surface(custom_engines=[{"name": "x"}])
    assert custom["agi_completion_claim"] is False

    # Empty
    empty = build_pgg_archon_agent_engine_surface(custom_engines=[])
    assert empty["agi_completion_claim"] is False
