from __future__ import annotations

import pytest

from agent.pgg_archon_llm_coordination import probe_llm_coordination
from agent.pgg_archon_super_routing import probe_super_routing
from agent.pgg_archon_background_grounding import probe_background_grounding


def test_llm_coordination_runs() -> None:
    p = probe_llm_coordination()
    assert p.name == "llm_coordination"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "custom_providers_count" in p.probes


def test_super_routing_runs() -> None:
    p = probe_super_routing()
    assert p.name == "super_routing"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "pgg_background_evolution_files" in p.probes


def test_background_grounding_runs() -> None:
    p = probe_background_grounding()
    assert p.name == "background_grounding"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "background_manifest_present" in p.probes
