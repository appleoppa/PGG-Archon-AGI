from __future__ import annotations

from pathlib import Path

import pytest

from agent.pgg_archon_final_state_bootstrap import bootstrap_final


def test_bootstrap_final_creates_files() -> None:
    summary = bootstrap_final()
    assert len(summary["written"]) >= 7
    for p in summary["written"]:
        assert Path(p).exists()
