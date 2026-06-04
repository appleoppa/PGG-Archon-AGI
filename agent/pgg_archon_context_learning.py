"""Bounded PGG Archon Context Learning — file-04 (real surface).

Implements 4-probe status surface for context learning:
  1. agent/ contains memory_retrieval modules
  2. ~/.hermes/data/memory has at least 1 file
  3. env CONTEXT_LEARNING_VERSION is set
  4. ~/.hermes/workspace is writable
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ContextLearningProbe:
    name: str
    status: str
    probes: dict[str, str]
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_cli(cli: str) -> str:
    return "available" if shutil.which(cli) else "missing"


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_context_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_context_learning() -> ContextLearningProbe:
    agent_dir = Path("/Users/appleoppa/.hermes/hermes-agent/agent")
    memory_dir = Path.home() / ".hermes" / "data" / "memory"
    mem_count = len([p for p in memory_dir.glob("*") if p.is_file()]) if memory_dir.exists() else 0
    mem_module_count = len(list(agent_dir.glob("*memory*.py"))) + len(list(agent_dir.glob("*context*.py"))) if agent_dir.exists() else 0
    deps = {
        "agent_memory_context_module_count": str(mem_module_count),
        "memory_file_count": str(mem_count),
        "env_CONTEXT_LEARNING_VERSION": _probe_env("CONTEXT_LEARNING_VERSION"),
        "path_~/.hermes/workspace": _probe_path_writable(Path.home() / ".hermes" / "workspace"),
    }
    present = (
        (1 if mem_module_count >= 1 else 0)
        + (1 if mem_count >= 1 else 0)
        + (1 if deps["env_CONTEXT_LEARNING_VERSION"] == "present" else 0)
        + (1 if deps["path_~/.hermes/workspace"] == "writable" else 0)
    )
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return ContextLearningProbe(
        name="context_learning",
        status=status,
        probes=deps,
        notes=f"Context learning new framework; {present}/4 surface gates resolved",
    )


def run_context_learning() -> dict[str, Any]:
    p = probe_context_learning()
    return {
        "schema": "PGGArchonContextLearning/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_context_learning(), ensure_ascii=False, indent=2))
