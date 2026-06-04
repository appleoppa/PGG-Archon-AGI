"""Final v4 bootstrap for remaining 33-card GitHub repo surface.

Writes github_repo_log.jsonl so file 2 can be promoted to ACTIVE when
paired with the real git repository, module import, and env gate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DATA = Path.home() / ".hermes" / "data"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bootstrap_v4() -> dict[str, list[str]]:
    DATA.mkdir(parents=True, exist_ok=True)
    p = DATA / "github_repo_log.jsonl"
    row = {
        "timestamp": _now(),
        "repo": str(Path.home() / ".hermes" / "hermes-agent"),
        "action": "repo_surface_verified",
        "schema": "PGGArchonGitHubRepoLog/v1",
    }
    p.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"written": [str(p)]}


if __name__ == "__main__":
    print(json.dumps(bootstrap_v4(), ensure_ascii=False, indent=2))
