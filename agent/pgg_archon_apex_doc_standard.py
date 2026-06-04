"""Bounded PGG Archon APEX Documentation Standard — file-22 (real surface).

4-probe status surface for APEX 文档规范 (APEX documentation standard):
  1. agent.pgg_archon_apex_doc_standard module is importable
  2. ~/.hermes/data/apex_doc_log.jsonl exists
  3. env PGG_ARCHON_APEX_DOC_VERSION is set
  4. agent/ contains ≥30 pgg_archon_*.py modules
"""

from __future__ import annotations

import importlib
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class APEXDocStandardProbe:
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


def probe_apex_doc_standard() -> APEXDocStandardProbe:
    log = Path.home() / ".hermes" / "data" / "apex_doc_log.jsonl"
    agent_dir = Path(__file__).resolve().parent
    pattern = re.compile(r"^pgg_archon_.*\.py$")
    modules = sorted([p.name for p in agent_dir.glob("pgg_archon_*.py")]) if agent_dir.exists() else []
    deps = {
        "module_apex_doc_standard": _probe_module("agent.pgg_archon_apex_doc_standard"),
        "apex_doc_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_APEX_DOC_VERSION": _probe_env("PGG_ARCHON_APEX_DOC_VERSION"),
        "pgg_archon_module_count": str(len(modules)),
    }
    present = 0
    if deps["module_apex_doc_standard"] == "importable":
        present += 1
    if deps["apex_doc_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_APEX_DOC_VERSION"] == "present":
        present += 1
    if len(modules) >= 30:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return APEXDocStandardProbe(
        name="apex_doc_standard",
        status=status,
        probes=deps,
        notes=f"APEX doc standard super-evolution 22-doc; {present}/4 surface gates resolved",
    )


def run_apex_doc_standard() -> dict[str, Any]:
    p = probe_apex_doc_standard()
    return {
        "schema": "PGGArchonAPEXDocStandard/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_apex_doc_standard(), ensure_ascii=False, indent=2))
