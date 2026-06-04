"""Bounded PGG Archon GitHub Repository — 33-card file 2 (real surface).

4-probe status surface for GitHub 仓库 / repo factory:
  1. agent.pgg_archon_github_repo module is importable
  2. git repository root exists and has commits
  3. env PGG_ARCHON_GITHUB_REPO_VERSION is set
  4. ~/.hermes/data/github_repo_log.jsonl exists
"""

from __future__ import annotations

import importlib
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class GitHubRepoProbe:
    name: str
    status: str
    probes: dict[str, str]
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_module(name: str) -> str:
    try:
        importlib.import_module(name)
        return "importable"
    except Exception:
        return "missing"


def _git_commit_count(repo: Path) -> int:
    try:
        out = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
        return int(out)
    except Exception:
        return 0


def probe_github_repo() -> GitHubRepoProbe:
    repo = Path.home() / ".hermes" / "hermes-agent"
    log = Path.home() / ".hermes" / "data" / "github_repo_log.jsonl"
    commits = _git_commit_count(repo)
    deps = {
        "module_github_repo": _probe_module("agent.pgg_archon_github_repo"),
        "git_commit_count": str(commits),
        "env_PGG_ARCHON_GITHUB_REPO_VERSION": _probe_env("PGG_ARCHON_GITHUB_REPO_VERSION"),
        "github_repo_log_present": "present" if log.exists() else "missing",
    }
    present = 0
    if deps["module_github_repo"] == "importable":
        present += 1
    if commits >= 1:
        present += 1
    if deps["env_PGG_ARCHON_GITHUB_REPO_VERSION"] == "present":
        present += 1
    if deps["github_repo_log_present"] == "present":
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return GitHubRepoProbe(
        name="github_repo",
        status=status,
        probes=deps,
        notes=f"GitHub repo factory 33-card-2; {present}/4 surface gates resolved",
    )


def run_github_repo() -> dict[str, Any]:
    p = probe_github_repo()
    return {
        "schema": "PGGArchonGitHubRepo/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_github_repo(), ensure_ascii=False, indent=2))
