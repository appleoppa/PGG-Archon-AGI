"""Bounded PGG Archon Closed-Loop Formula — file-27 (real surface).

4-probe status surface for pgg-archon-closed-loop-formula
(真实代入 → 短板暴露 → 外部学习 → 闭环):
  1. agent.pgg_archon_closed_loop_formula module is importable
  2. env PGG_ARCHON_CLOSED_LOOP_VERSION is set
  3. ~/.hermes/data/closed_loop_audit.jsonl exists
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
class ClosedLoopFormulaProbe:
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
        test = p / ".pgg_archon_closed_loop_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_closed_loop_formula() -> ClosedLoopFormulaProbe:
    audit_log = Path.home() / ".hermes" / "data" / "closed_loop_audit.jsonl"
    deps = {
        "module_closed_loop_formula": _probe_module("agent.pgg_archon_closed_loop_formula"),
        "env_PGG_ARCHON_CLOSED_LOOP_VERSION": _probe_env("PGG_ARCHON_CLOSED_LOOP_VERSION"),
        "closed_loop_audit_present": "present" if audit_log.exists() else "missing",
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
    return ClosedLoopFormulaProbe(
        name="closed_loop_formula",
        status=status,
        probes=deps,
        notes=f"Closed loop formula super-evolution 27; {present}/4 surface gates resolved",
    )


def run_closed_loop_formula() -> dict[str, Any]:
    p = probe_closed_loop_formula()
    return {
        "schema": "PGGArchonClosedLoopFormula/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_closed_loop_formula(), ensure_ascii=False, indent=2))
