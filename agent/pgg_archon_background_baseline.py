"""Bounded PGG Archon Background Forced Grounding Baseline — 33-card file 20 (real surface).

4-probe status surface for 后台强制固化基准公式 (background forced grounding baseline formula):
  1. agent.pgg_archon_background_baseline module is importable
  2. ~/.hermes/data/background_baseline_log.jsonl exists
  3. env PGG_ARCHON_BACKGROUND_BASELINE_VERSION is set
  4. ~/.hermes/data/pgg-background-evolution/manifest.jsonl exists
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class BackgroundBaselineProbe:
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


def probe_background_baseline() -> BackgroundBaselineProbe:
    log = Path.home() / ".hermes" / "data" / "background_baseline_log.jsonl"
    manifest = Path.home() / ".hermes" / "data" / "pgg-background-evolution" / "manifest.jsonl"
    deps = {
        "module_background_baseline": _probe_module("agent.pgg_archon_background_baseline"),
        "background_baseline_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_BACKGROUND_BASELINE_VERSION": _probe_env("PGG_ARCHON_BACKGROUND_BASELINE_VERSION"),
        "background_manifest_present": "present" if manifest.exists() else "missing",
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
    return BackgroundBaselineProbe(
        name="background_baseline",
        status=status,
        probes=deps,
        notes=f"Background forced grounding baseline 33-card-20; {present}/4 surface gates resolved",
    )


def run_background_baseline() -> dict[str, Any]:
    p = probe_background_baseline()
    return {
        "schema": "PGGArchonBackgroundBaseline/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_background_baseline(), ensure_ascii=False, indent=2))
