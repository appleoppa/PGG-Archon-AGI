"""Bounded PGG Archon EvoMaster Native Evolution Core — file-09 (real surface).

4-probe status surface for EvoMaster native evolution core formula:
  1. agent.pgg_archon_evomaster module is importable
  2. ~/.hermes/data/evomaster_state.jsonl or similar state log exists
  3. env PGG_ARCHON_EVOMASTER_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl exists (audit trail)
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
class EvoMasterProbe:
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


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_evomaster_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_evomaster() -> EvoMasterProbe:
    evo_state = Path.home() / ".hermes" / "data" / "evomaster_state.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    deps = {
        "module_evomaster": _probe_module("agent.pgg_archon_evomaster_core"),
        "evomaster_state_present": "present" if evo_state.exists() else "missing",
        "env_PGG_ARCHON_EVOMASTER_VERSION": _probe_env("PGG_ARCHON_EVOMASTER_VERSION"),
        "audit_trail_present": "present" if audit.exists() else "missing",
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
    return EvoMasterProbe(
        name="evomaster",
        status=status,
        probes=deps,
        notes=f"EvoMaster native evolution core super-evolution 9; {present}/4 surface gates resolved",
    )


def run_evomaster() -> dict[str, Any]:
    p = probe_evomaster()
    return {
        "schema": "PGGArchonEvoMaster/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_evomaster(), ensure_ascii=False, indent=2))
