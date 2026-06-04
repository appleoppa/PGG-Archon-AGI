"""Bounded PGG Archon Delta G Evolution Paradigm — file-14 (real surface).

4-probe status surface for ΔG 演化范式 (delta-G evolution paradigm):
  1. agent.pgg_archon_delta_g_evolution module is importable
  2. ~/.hermes/data/delta_g_log.jsonl exists
  3. env PGG_ARCHON_DELTA_G_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl has ≥1 line
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class DeltaGProbe:
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


def probe_delta_g() -> DeltaGProbe:
    log = Path.home() / ".hermes" / "data" / "delta_g_log.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    audit_lines = sum(1 for _ in audit.open("r", encoding="utf-8")) if audit.exists() else 0
    deps = {
        "module_delta_g_evolution": _probe_module("agent.pgg_archon_delta_g_evolution"),
        "delta_g_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_DELTA_G_VERSION": _probe_env("PGG_ARCHON_DELTA_G_VERSION"),
        "audit_trail_lines": str(audit_lines),
    }
    present = 0
    if deps["module_delta_g_evolution"] == "importable":
        present += 1
    if deps["delta_g_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_DELTA_G_VERSION"] == "present":
        present += 1
    if audit_lines >= 1:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return DeltaGProbe(
        name="delta_g_evolution",
        status=status,
        probes=deps,
        notes=f"ΔG evolution paradigm super-evolution 14; {present}/4 surface gates resolved",
    )


def run_delta_g() -> dict[str, Any]:
    p = probe_delta_g()
    return {
        "schema": "PGGArchonDeltaG/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_delta_g(), ensure_ascii=False, indent=2))
