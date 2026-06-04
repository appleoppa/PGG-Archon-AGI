from __future__ import annotations

import pytest

from agent.pgg_archon_context_learning import probe_context_learning
from agent.pgg_archon_memory_system import probe_memory_system


def test_context_learning_runs() -> None:
    p = probe_context_learning()
    assert p.name == "context_learning"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "memory_file_count" in p.probes


def test_memory_system_runs() -> None:
    p = probe_memory_system()
    assert p.name == "memory_system"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "memory_db_present" in p.probes
