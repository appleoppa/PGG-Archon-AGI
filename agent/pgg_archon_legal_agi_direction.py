"""Bounded PGG Archon Top Legal AGI Evolution Direction — 33-card file 26 (real surface).

4-probe status surface for 全球顶级法律AGI进化方向 (global top legal AGI evolution direction):
  1. agent.pgg_archon_legal_agi_direction module is importable
  2. ~/.hermes/data/legal_agi_direction_log.jsonl exists
  3. env PGG_ARCHON_LEGAL_AGI_DIRECTION_VERSION is set
  4. ~/.hermes/data/pgg_archon.db has at least 1 active legal record
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
class LegalAGIDirectionProbe:
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


def probe_legal_agi_direction() -> LegalAGIDirectionProbe:
    log = Path.home() / ".hermes" / "data" / "legal_agi_direction_log.jsonl"
    db = Path.home() / ".hermes" / "data" / "pgg_archon.db"
    db_active = 0
    if db.exists():
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t} WHERE active=1")
                    db_active += cur.fetchone()[0]
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass
    deps = {
        "module_legal_agi_direction": _probe_module("agent.pgg_archon_legal_agi_direction"),
        "legal_agi_direction_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_LEGAL_AGI_DIRECTION_VERSION": _probe_env("PGG_ARCHON_LEGAL_AGI_DIRECTION_VERSION"),
        "pgg_archon_db_active_records": str(db_active),
    }
    present = 0
    if deps["module_legal_agi_direction"] == "importable":
        present += 1
    if deps["legal_agi_direction_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_LEGAL_AGI_DIRECTION_VERSION"] == "present":
        present += 1
    if db_active >= 1:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return LegalAGIDirectionProbe(
        name="legal_agi_direction",
        status=status,
        probes=deps,
        notes=f"Top legal AGI evolution direction 33-card-26; {present}/4 surface gates resolved",
    )


def run_legal_agi_direction() -> dict[str, Any]:
    p = probe_legal_agi_direction()
    return {
        "schema": "PGGArchonLegalAGIDirection/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_legal_agi_direction(), ensure_ascii=False, indent=2))
