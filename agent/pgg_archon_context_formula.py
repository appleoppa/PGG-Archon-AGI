"""Bounded PGG Archon Context Formula — file-4.5 (real surface).

4-probe status surface for 上下文公式 (context formula):
  1. agent.pgg_archon_context_formula module is importable
  2. ~/.hermes/data/context_formula_log.jsonl exists
  3. env PGG_ARCHON_CONTEXT_FORMULA_VERSION is set
  4. ~/.hermes/memories/MEMORY.md is present
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ContextFormulaProbe:
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


def probe_context_formula() -> ContextFormulaProbe:
    log = Path.home() / ".hermes" / "data" / "context_formula_log.jsonl"
    mem_md = Path.home() / ".hermes" / "memories" / "MEMORY.md"
    deps = {
        "module_context_formula": _probe_module("agent.pgg_archon_context_formula"),
        "context_formula_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_CONTEXT_FORMULA_VERSION": _probe_env("PGG_ARCHON_CONTEXT_FORMULA_VERSION"),
        "MEMORY_md_present": "present" if mem_md.exists() else "missing",
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
    return ContextFormulaProbe(
        name="context_formula",
        status=status,
        probes=deps,
        notes=f"Context formula super-evolution 4.5; {present}/4 surface gates resolved",
    )


def run_context_formula() -> dict[str, Any]:
    p = probe_context_formula()
    return {
        "schema": "PGGArchonContextFormula/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_context_formula(), ensure_ascii=False, indent=2))
