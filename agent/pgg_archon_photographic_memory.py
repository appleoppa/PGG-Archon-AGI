"""Bounded PGG Archon Photographic Memory — file-16 (real surface).

4-probe status surface for 过目不忘 (photographic memory / persistent memory retrieval):
  1. agent.pgg_archon_photographic_memory module is importable
  2. ~/.hermes/data/memory.db has ≥10 rows
  3. env PGG_ARCHON_PHOTOGRAPHIC_MEMORY_VERSION is set
  4. ~/.hermes/memories/MEMORY.md is readable
"""

from __future__ import annotations

import importlib
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PhotographicMemoryProbe:
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


def probe_photographic_memory() -> PhotographicMemoryProbe:
    mem_db = Path.home() / ".hermes" / "data" / "memory.db"
    mem_md = Path.home() / ".hermes" / "memories" / "MEMORY.md"
    row_count = 0
    if mem_db.exists():
        try:
            conn = sqlite3.connect(mem_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memory")
            row_count = cur.fetchone()[0]
            conn.close()
        except Exception:
            row_count = 0
    deps = {
        "module_photographic_memory": _probe_module("agent.pgg_archon_photographic_memory"),
        "memory_db_rows": str(row_count),
        "env_PGG_ARCHON_PHOTOGRAPHIC_MEMORY_VERSION": _probe_env("PGG_ARCHON_PHOTOGRAPHIC_MEMORY_VERSION"),
        "MEMORY_md_readable": "present" if mem_md.exists() else "missing",
    }
    present = 0
    if deps["module_photographic_memory"] == "importable":
        present += 1
    if row_count >= 10:
        present += 1
    if deps["env_PGG_ARCHON_PHOTOGRAPHIC_MEMORY_VERSION"] == "present":
        present += 1
    if deps["MEMORY_md_readable"] == "present":
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return PhotographicMemoryProbe(
        name="photographic_memory",
        status=status,
        probes=deps,
        notes=f"Photographic memory super-evolution 16; {present}/4 surface gates resolved",
    )


def run_photographic_memory() -> dict[str, Any]:
    p = probe_photographic_memory()
    return {
        "schema": "PGGArchonPhotographicMemory/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_photographic_memory(), ensure_ascii=False, indent=2))
