"""Bounded PGG Archon CMMI Industrial Standard — file-18 (real surface).

4-probe status surface for CMMI 工业化标准 (CMMI industrial standard):
  1. agent.pgg_archon_cmmi_industrial module is importable
  2. ~/.hermes/data/cmmi_audit_log.jsonl exists
  3. env PGG_ARCHON_CMMI_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl has ≥3 lines
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CMMIProbe:
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


def probe_cmmi() -> CMMIProbe:
    log = Path.home() / ".hermes" / "data" / "cmmi_audit_log.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    audit_lines = sum(1 for _ in audit.open("r", encoding="utf-8")) if audit.exists() else 0
    deps = {
        "module_cmmi": _probe_module("agent.pgg_archon_cmmi_industrial"),
        "cmmi_audit_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_CMMI_VERSION": _probe_env("PGG_ARCHON_CMMI_VERSION"),
        "audit_trail_lines": str(audit_lines),
    }
    present = 0
    if deps["module_cmmi"] == "importable":
        present += 1
    if deps["cmmi_audit_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_CMMI_VERSION"] == "present":
        present += 1
    if audit_lines >= 3:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return CMMIProbe(
        name="cmmi",
        status=status,
        probes=deps,
        notes=f"CMMI industrial standard super-evolution 18; {present}/4 surface gates resolved",
    )


def run_cmmi() -> dict[str, Any]:
    p = probe_cmmi()
    return {
        "schema": "PGGArchonCMMI/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_cmmi(), ensure_ascii=False, indent=2))
