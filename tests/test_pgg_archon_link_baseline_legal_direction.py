from __future__ import annotations

import pytest

from agent.pgg_archon_link_integration import probe_link_integration
from agent.pgg_archon_background_baseline import probe_background_baseline
from agent.pgg_archon_legal_agi_direction import probe_legal_agi_direction


def test_link_integration_runs() -> None:
    p = probe_link_integration()
    assert p.name == "link_integration"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "audit_trail_lines" in p.probes


def test_background_baseline_runs() -> None:
    p = probe_background_baseline()
    assert p.name == "background_baseline"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "background_manifest_present" in p.probes


def test_legal_agi_direction_runs() -> None:
    p = probe_legal_agi_direction()
    assert p.name == "legal_agi_direction"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "pgg_archon_db_active_records" in p.probes
