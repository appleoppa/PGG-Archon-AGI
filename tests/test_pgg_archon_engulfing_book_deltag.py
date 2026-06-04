from __future__ import annotations

import pytest

from agent.pgg_archon_engulfing_self_evolution import probe_engulfing_self_evolution
from agent.pgg_archon_book_to_skill import probe_book_to_skill
from agent.pgg_archon_delta_g_evolution import probe_delta_g


def test_engulfing_self_evolution_runs() -> None:
    p = probe_engulfing_self_evolution()
    assert p.name == "engulfing_self_evolution"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes


def test_book_to_skill_runs() -> None:
    p = probe_book_to_skill()
    assert p.name == "book_to_skill"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "skills_subdir_count" in p.probes


def test_delta_g_runs() -> None:
    p = probe_delta_g()
    assert p.name == "delta_g_evolution"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes
