"""Bounded PGG Archon Memory System — file-05 (real surface).

4-probe status surface for memory system:
  1. ~/.hermes/data has memory.db
  2. memory_retrieval_architecture module is importable
  3. env PGG_ARCHON_MEMORY_VERSION is set
  4. ~/.hermes/memories exists
"""

from __future__ import annotations

import importlib
import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemorySystemProbe:
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
        test = p / ".pgg_archon_memory_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def _probe_module(name: str) -> str:
    try:
        importlib.import_module(name)
        return "importable"
    except Exception:
        return "missing"


def probe_memory_system() -> MemorySystemProbe:
    mem_db = Path.home() / ".hermes" / "data" / "memory.db"
    mem_dir = Path.home() / ".hermes" / "memories"
    deps = {
        "memory_db_present": "present" if mem_db.exists() else "missing",
        "module_memory_retrieval_architecture": _probe_module("agent.pgg_archon_memory_retrieval_architecture"),
        "env_PGG_ARCHON_MEMORY_VERSION": _probe_env("PGG_ARCHON_MEMORY_VERSION"),
        "path_~/.hermes/memories": _probe_path_writable(mem_dir),
    }
    present = 0
    if deps["memory_db_present"] == "present":
        present += 1
    if deps["module_memory_retrieval_architecture"] == "importable":
        present += 1
    if deps["env_PGG_ARCHON_MEMORY_VERSION"] == "present":
        present += 1
    if deps["path_~/.hermes/memories"] == "writable":
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return MemorySystemProbe(
        name="memory_system",
        status=status,
        probes=deps,
        notes=f"Memory system; {present}/4 surface gates resolved",
    )


def run_memory_system() -> dict[str, Any]:
    p = probe_memory_system()
    return {
        "schema": "PGGArchonMemorySystem/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_memory_system(), ensure_ascii=False, indent=2))
