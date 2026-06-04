from __future__ import annotations

import pytest

from agent.pgg_archon_token_hygiene import probe_token_hygiene
from agent.pgg_archon_full_toolcall_integration import probe_toolcall_integration


def test_token_hygiene_runs() -> None:
    p = probe_token_hygiene()
    assert p.name == "token_hygiene"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_dir_files" in p.probes


def test_toolcall_integration_runs() -> None:
    p = probe_toolcall_integration()
    assert p.name == "toolcall_integration"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "agent_toolcall_module_count" in p.probes
