"""Bounded PGG Archon Engulfing Self-Evolution — file-12 (real surface).

4-probe status surface for 吞噬自进化 (engulfing self-evolution / absorbing external repos):
  1. agent.pgg_archon_engulfing_self_evolution module is importable
  2. ~/.hermes/data/engulfing_log.jsonl exists
  3. env PGG_ARCHON_ENGULFING_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl has ≥2 lines (engulfing requires cycle logs)
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class EngulfingSelfEvolutionProbe:
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


def probe_engulfing_self_evolution() -> EngulfingSelfEvolutionProbe:
    log = Path.home() / ".hermes" / "data" / "engulfing_log.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    audit_lines = sum(1 for _ in audit.open("r", encoding="utf-8")) if audit.exists() else 0
    deps = {
        "module_engulfing_self_evolution": _probe_module("agent.pgg_archon_engulfing_self_evolution"),
        "engulfing_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_ENGULFING_VERSION": _probe_env("PGG_ARCHON_ENGULFING_VERSION"),
        "audit_trail_lines": str(audit_lines),
    }
    present = 0
    if deps["module_engulfing_self_evolution"] == "importable":
        present += 1
    if deps["engulfing_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_ENGULFING_VERSION"] == "present":
        present += 1
    if audit_lines >= 2:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return EngulfingSelfEvolutionProbe(
        name="engulfing_self_evolution",
        status=status,
        probes=deps,
        notes=f"Engulfing self-evolution super-evolution 12; {present}/4 surface gates resolved",
    )


def run_engulfing_self_evolution() -> dict[str, Any]:
    p = probe_engulfing_self_evolution()
    return {
        "schema": "PGGArchonEngulfingSelfEvolution/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_engulfing_self_evolution(), ensure_ascii=False, indent=2))
