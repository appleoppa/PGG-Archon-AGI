from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_tiangong_four_core import run_tiangong, probe_evolver


def test_tiangong_runs() -> None:
    summary = run_tiangong()
    assert summary["schema"] == "PGGArchonTiangongFourCore/v1"
    assert len(summary["cores"]) == 4
    statuses = {c["name"]: c["status"] for c in summary["cores"]}
    assert set(statuses.keys()) == {"evolver", "autoresearch", "openhands", "superpowers"}
    for s in statuses.values():
        assert s in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}


def test_tiangong_active_count_within_range() -> None:
    summary = run_tiangong()
    total = summary["active_count"] + summary["partial_count"] + summary["skeleton_count"] + summary["absent_count"]
    assert total == 4


def test_probe_evolver_runs() -> None:
    c = probe_evolver()
    assert c.name == "evolver"
    assert c.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "module_pgg_archon_apex_engine" in c.probes
