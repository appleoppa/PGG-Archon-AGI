from __future__ import annotations

import pytest

from agent.pgg_archon_context_formula import probe_context_formula
from agent.pgg_archon_cmmi_industrial import probe_cmmi
from agent.pgg_archon_apex_doc_standard import probe_apex_doc_standard


def test_context_formula_runs() -> None:
    p = probe_context_formula()
    assert p.name == "context_formula"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "MEMORY_md_present" in p.probes


def test_cmmi_runs() -> None:
    p = probe_cmmi()
    assert p.name == "cmmi"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes
    assert "rust_cmmi_gate" in p.probes
    assert "rust_cmmi_gate_status" in p.probes


def test_apex_doc_standard_runs() -> None:
    p = probe_apex_doc_standard()
    assert p.name == "apex_doc_standard"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "pgg_archon_module_count" in p.probes
