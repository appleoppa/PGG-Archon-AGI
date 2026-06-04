from __future__ import annotations

import pytest

from agent.pgg_archon_multi_agent_collaboration import probe_multi_agent_collaboration
from agent.pgg_archon_deep_self_evolution import probe_deep_self_evolution
from agent.pgg_archon_research_engine import probe_research_engine


def test_multi_agent_collaboration_runs() -> None:
    p = probe_multi_agent_collaboration()
    assert p.name == "multi_agent_collaboration"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "orchestrator_module_count" in p.probes


def test_deep_self_evolution_runs() -> None:
    p = probe_deep_self_evolution()
    assert p.name == "deep_self_evolution"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes


def test_research_engine_runs() -> None:
    p = probe_research_engine()
    assert p.name == "research_engine"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "arxiv_papers_present" in p.probes
