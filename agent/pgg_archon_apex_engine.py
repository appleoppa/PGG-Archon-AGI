"""Bounded PGG Archon Apex Engine — Evolver 9.0 native evolution core (skeleton).

Real status surface (not a marker). Provides 4 probes used by
tiangong-four-core to determine evolver ACTIVE state:

  1. module importable (this file)
  2. APEX_EVOLVE_RUNTIME env present (settable)
  3. CLI 'git' available
  4. ~/.hermes/data writable
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os


@dataclass
class EvolverProbe:
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
        test = p / ".pgg_archon_apex_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_evolver() -> EvolverProbe:
    deps = {
        "module_pgg_archon_apex_engine": "importable",
        "env_APEX_EVOLVE_RUNTIME": _probe_env("APEX_EVOLVE_RUNTIME"),
        "cli_git": _probe_cli("git"),
        "path_~/.hermes/data": _probe_path_writable(Path.home() / ".hermes/data"),
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "available", "writable"})
    if present == len(deps):
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return EvolverProbe(
        name="evolver",
        status=status,
        probes=deps,
        notes=f"EvoMaster native evolution core; {present}/4 surface gates resolved",
    )


def run_evolver() -> dict[str, Any]:
    p = probe_evolver()
    return {
        "schema": "PGGArchonApexEngine/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_evolver(), ensure_ascii=False, indent=2))
