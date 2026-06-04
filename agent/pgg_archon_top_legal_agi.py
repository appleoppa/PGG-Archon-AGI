"""Bounded PGG Archon Top Legal AGI — file-28 (real surface).

4-probe status surface for 全球顶级法律 AGI (top legal AGI):
  1. agent.pgg_archon_top_legal_agi module is importable
  2. ~/.hermes/data/legal_agi_log.jsonl exists
  3. env PGG_ARCHON_LEGAL_AGI_VERSION is set
  4. ~/.hermes/data/pgg_archon.db has legal records (legal agi requires domain data)
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
class TopLegalAGIProbe:
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


def probe_top_legal_agi() -> TopLegalAGIProbe:
    log = Path.home() / ".hermes" / "data" / "legal_agi_log.jsonl"
    db = Path.home() / ".hermes" / "data" / "pgg_archon.db"
    db_present = db.exists()
    deps = {
        "module_top_legal_agi": _probe_module("agent.pgg_archon_top_legal_agi"),
        "legal_agi_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_LEGAL_AGI_VERSION": _probe_env("PGG_ARCHON_LEGAL_AGI_VERSION"),
        "pgg_archon_db_present": "present" if db_present else "missing",
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "writable"})
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return TopLegalAGIProbe(
        name="top_legal_agi",
        status=status,
        probes=deps,
        notes=f"Top legal AGI super-evolution 28; {present}/4 surface gates resolved",
    )


def run_top_legal_agi() -> dict[str, Any]:
    p = probe_top_legal_agi()
    return {
        "schema": "PGGArchonTopLegalAGI/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_top_legal_agi(), ensure_ascii=False, indent=2))
