from __future__ import annotations

from pathlib import Path

import pytest

from agent.pgg_archon_final_state_bootstrap_v3 import bootstrap_v3


def test_bootstrap_v3_creates_files() -> None:
    summary = bootstrap_v3()
    assert len(summary["written"]) >= 3
    for p in summary["written"]:
        assert Path(p).exists()
