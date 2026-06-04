from __future__ import annotations

import pytest

from agent.pgg_archon_apex_master_formula import probe_apex_master_formula
from agent.pgg_archon_evomap_toolchain import probe_evomap_toolchain
from agent.pgg_archon_closed_loop_formula import probe_closed_loop_formula


def test_apex_master_formula_runs() -> None:
    p = probe_apex_master_formula()
    assert p.name == "apex_master_formula"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "module_apex_engine" in p.probes


def test_evomap_toolchain_runs() -> None:
    p = probe_evomap_toolchain()
    assert p.name == "evomap_toolchain"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "module_evomap_toolchain" in p.probes


def test_closed_loop_formula_runs() -> None:
    p = probe_closed_loop_formula()
    assert p.name == "closed_loop_formula"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "closed_loop_audit_present" in p.probes
