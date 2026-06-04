from __future__ import annotations

import pytest

from agent.pgg_archon_apex_skill import probe_apex_skill
from agent.pgg_archon_llm_mutual_constraint import mutual_check, MutualCheckResult


def test_apex_skill_runs() -> None:
    p = probe_apex_skill()
    assert p.name == "apex_skill"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "skill_count" in p.probes


def test_mutual_check_runs() -> None:
    result = mutual_check("test-target", "All probes return real env signals.")
    assert isinstance(result, MutualCheckResult)
    assert result.target == "test-target"
    assert result.overall_verdict in {"OK", "CONFLICT", "UNAVAILABLE"}
    assert isinstance(result.per_auditor, dict)
