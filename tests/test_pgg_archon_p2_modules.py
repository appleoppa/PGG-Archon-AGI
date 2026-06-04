from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_tiangong_skill import collect_tiangong_status, TIANGONG_FOUR_CORE_NAMES
from agent.pgg_archon_research_unified_engine import collect_research_artifacts, ARTIFACT_HINTS


def test_tiangong_four_core_names_complete() -> None:
    assert TIANGONG_FOUR_CORE_NAMES == ["evolver", "autoresearch", "openhands", "superpowers"]


def test_tiangong_collect_returns_valid_status(tmp_path: Path) -> None:
    data = collect_tiangong_status(home=tmp_path)
    assert data["schema"] == "PGGArchonTiangongStatus/v1"
    assert len(data["cores"]) == 4
    states = {c["name"]: c["state"] for c in data["cores"]}
    # With an empty tmp_path, only declared-but-absent evidence will return state='absent'
    # openhands has no evidence paths declared, so its state should be 'absent'.
    assert states["openhands"] == "absent"


def test_research_engine_collect_returns_skeleton(tmp_path: Path) -> None:
    data = collect_research_artifacts(home=tmp_path)
    assert data["schema"] == "PGGArchonResearchUnifiedEngineStatus/v1"
    assert data["engine_state"] == "SKELETON"
    assert isinstance(data["evidence"], list)
    assert "boundary" in data
