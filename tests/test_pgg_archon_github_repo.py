from __future__ import annotations

from pathlib import Path

from agent.pgg_archon_github_repo import probe_github_repo


def test_github_repo_runs() -> None:
    p = probe_github_repo()
    assert p.name == "github_repo"
    assert p.status in {"ABSENT", "SKELETON", "PARTIAL", "ACTIVE"}
    assert "git_commit_count" in p.probes
