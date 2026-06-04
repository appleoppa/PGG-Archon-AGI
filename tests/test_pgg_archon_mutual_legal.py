from __future__ import annotations

import pytest

from agent.pgg_archon_multi_llm_constraint import probe_multi_llm_constraint
from agent.pgg_archon_top_legal_agi import probe_top_legal_agi


def test_multi_llm_constraint_runs() -> None:
    p = probe_multi_llm_constraint()
    assert p.name == "multi_llm_constraint"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes


def test_top_legal_agi_runs() -> None:
    p = probe_top_legal_agi()
    assert p.name == "top_legal_agi"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "pgg_archon_db_present" in p.probes
