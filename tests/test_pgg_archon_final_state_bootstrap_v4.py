from __future__ import annotations

from pathlib import Path

from agent.pgg_archon_final_state_bootstrap_v4 import bootstrap_v4


def test_bootstrap_v4_creates_github_repo_log() -> None:
    summary = bootstrap_v4()
    assert len(summary["written"]) == 1
    assert Path(summary["written"][0]).exists()
