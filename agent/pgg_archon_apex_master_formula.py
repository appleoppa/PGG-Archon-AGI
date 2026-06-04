"""Bounded PGG Archon APEX Master Formula — file-0.5 (real surface).

4-probe status surface for APEX 全体系公式 (master formula / 12 factors / state card baseline):
  1. agent.pgg_archon_apex_engine module is importable
  2. env APEX_ENGINE_VERSION is set
  3. ~/.hermes/data/apex_state_card.jsonl exists
  4. ~/.hermes/data is writable
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
class APEXMasterFormulaProbe:
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
        test = p / ".pgg_archon_apex_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_apex_master_formula() -> APEXMasterFormulaProbe:
    apex_state = Path.home() / ".hermes" / "data" / "apex_state_card.jsonl"
    deps = {
        "module_apex_engine": _probe_module("agent.pgg_archon_apex_engine"),
        "env_APEX_ENGINE_VERSION": _probe_env("APEX_ENGINE_VERSION"),
        "apex_state_card_present": "present" if apex_state.exists() else "missing",
        "path_~/.hermes/data": _probe_path_writable(Path.home() / ".hermes" / "data"),
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
    return APEXMasterFormulaProbe(
        name="apex_master_formula",
        status=status,
        probes=deps,
        notes=f"APEX master formula super-evolution 0.5; {present}/4 surface gates resolved",
    )


def run_apex_master_formula() -> dict[str, Any]:
    p = probe_apex_master_formula()
    return {
        "schema": "PGGArchonAPEXMasterFormula/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_apex_master_formula(), ensure_ascii=False, indent=2))
