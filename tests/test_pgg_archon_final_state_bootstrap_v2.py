from __future__ import annotations

from pathlib import Path

import pytest

from agent.pgg_archon_final_state_bootstrap_v2 import bootstrap_v2


def test_bootstrap_v2_creates_files() -> None:
    summary = bootstrap_v2()
    assert len(summary["written"]) >= 3
    for p in summary["written"]:
        assert Path(p).exists()
