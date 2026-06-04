from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_state_bootstrap import bootstrap
from agent.pgg_archon_apex_master_formula import probe_apex_master_formula
from agent.pgg_archon_evomap_toolchain import probe_evomap_toolchain
from agent.pgg_archon_closed_loop_formula import probe_closed_loop_formula
from agent.pgg_archon_core_cognition import probe_core_cognition
from agent.pgg_archon_memory_system import probe_memory_system
from agent.pgg_archon_evomaster import probe_evomaster


def test_bootstrap_creates_files() -> None:
    summary = bootstrap()
    assert len(summary["written"]) >= 6
    for p in summary["written"]:
        assert Path(p).exists()


def test_apex_master_formula_advances_to_active() -> None:
    bootstrap()
    p = probe_apex_master_formula()
    assert p.status == "ACTIVE"


def test_evomap_toolchain_advances_to_active() -> None:
    bootstrap()
    p = probe_evomap_toolchain()
    assert p.status == "ACTIVE"


def test_closed_loop_formula_advances_to_active() -> None:
    bootstrap()
    p = probe_closed_loop_formula()
    assert p.status == "ACTIVE"


def test_core_cognition_advances_to_active() -> None:
    bootstrap()
    p = probe_core_cognition()
    assert p.status == "ACTIVE"


def test_memory_system_advances_to_active() -> None:
    bootstrap()
    p = probe_memory_system()
    assert p.status == "ACTIVE"


def test_evomaster_advances_to_active() -> None:
    bootstrap()
    p = probe_evomaster()
    assert p.status == "ACTIVE"
