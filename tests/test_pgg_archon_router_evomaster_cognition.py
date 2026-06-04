from __future__ import annotations

import pytest

from agent.pgg_archon_quantum_channel_router import probe_quantum_channel_router
from agent.pgg_archon_evomaster import probe_evomaster
from agent.pgg_archon_core_cognition import probe_core_cognition


def test_quantum_channel_router_runs() -> None:
    p = probe_quantum_channel_router()
    assert p.name == "quantum_channel_router"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "module_quantum_channel_router" in p.probes


def test_evomaster_runs() -> None:
    p = probe_evomaster()
    assert p.name == "evomaster"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "module_evomaster" in p.probes


def test_core_cognition_runs() -> None:
    p = probe_core_cognition()
    assert p.name == "core_cognition"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "AGENTS_md_writable" in p.probes
