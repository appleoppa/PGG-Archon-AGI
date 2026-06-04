from __future__ import annotations

import pytest

from agent.pgg_archon_personal_agent import probe_personal_agent
from agent.pgg_archon_photographic_memory import probe_photographic_memory
from agent.pgg_archon_fusion import probe_fusion


def test_personal_agent_runs() -> None:
    p = probe_personal_agent()
    assert p.name == "personal_agent"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "USER_md_writable" in p.probes


def test_photographic_memory_runs() -> None:
    p = probe_photographic_memory()
    assert p.name == "photographic_memory"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "memory_db_rows" in p.probes


def test_fusion_runs() -> None:
    p = probe_fusion()
    assert p.name == "fusion"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes
