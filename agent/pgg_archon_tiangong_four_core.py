"""Bounded PGG Archon Tiangong Four-Core — 4-core orchestrator surface.

Implements the four super-evolution cores (file 11) as a real
status surface, not a marker-only placeholder. Each core is a
small dataclass + 4 status probes that exercise the surface end
to end (env, key, log, runtime). No silent fabrication; missing
dependencies report as ABSENT.

Cores:
  1. evolver      — Evolver 9.0 native evolution core
  2. autoresearch — Auto-research loop
  3. openhands    — OpenHands-style code agent
  4. superpowers  — Super-powers skill / composition
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CoreStatus:
    name: str
    status: str  # ABSENT | SKELETON | PARTIAL | ACTIVE
    dependencies_resolved: list[str] = field(default_factory=list)
    dependencies_missing: list[str] = field(default_factory=list)
    probes: dict[str, str] = field(default_factory=dict)
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_python_module(module_name: str) -> str:
    try:
        importlib.import_module(module_name)
        return "importable"
    except Exception:
        return "missing"


def _probe_cli(cli: str) -> str:
    return "available" if shutil.which(cli) else "missing"


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_tiangong_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_evolver() -> CoreStatus:
    deps = {
        "module_pgg_archon_apex_engine": _probe_python_module("agent.pgg_archon_apex_engine"),
        "env_APEX_EVOLVE_RUNTIME": _probe_env("APEX_EVOLVE_RUNTIME"),
        "cli_git": _probe_cli("git"),
        "path_~/.hermes/data": _probe_path_writable(Path.home() / ".hermes/data"),
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "available", "writable"})
    if present == 0:
        status = "ABSENT"
    elif present < 2:
        status = "SKELETON"
    elif present < len(deps):
        status = "PARTIAL"
    else:
        status = "ACTIVE"
    return CoreStatus(
        name="evolver",
        status=status,
        dependencies_resolved=[k for k, v in deps.items() if v in {"importable", "present", "available", "writable"}],
        dependencies_missing=[k for k, v in deps.items() if v in {"missing", "not_writable"}],
        probes=deps,
        notes="EvoMaster native evolution core; 4/4 ACTIVE means all surface gates resolved",
    )


def probe_autoresearch() -> CoreStatus:
    deps = {
        "module_pgg_archon_research_unified_engine": _probe_python_module("agent.pgg_archon_research_unified_engine"),
        "env_ARXIV_API_KEY": _probe_env("ARXIV_API_KEY"),
        "cli_curl": _probe_cli("curl"),
        "path_~/.hermes/data/audit": _probe_path_writable(Path.home() / ".hermes/data/audit"),
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "available", "writable"})
    if present == 0:
        status = "ABSENT"
    elif present < 2:
        status = "SKELETON"
    elif present < len(deps):
        status = "PARTIAL"
    else:
        status = "ACTIVE"
    return CoreStatus(
        name="autoresearch",
        status=status,
        dependencies_resolved=[k for k, v in deps.items() if v in {"importable", "present", "available", "writable"}],
        dependencies_missing=[k for k, v in deps.items() if v in {"missing", "not_writable"}],
        probes=deps,
        notes="Auto-research loop; 4/4 ACTIVE means engine+key+cli+log all resolved",
    )


def probe_openhands() -> CoreStatus:
    deps = {
        "module_pgg_archon_code_agent": _probe_python_module("agent.pgg_archon_code_agent"),
        "env_OPENHANDS_RUNTIME": _probe_env("OPENHANDS_RUNTIME"),
        "cli_node": _probe_cli("node"),
        "path_/tmp/pgg_archon_workspace": _probe_path_writable(Path("/tmp") / "pgg_archon_workspace"),
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "available", "writable"})
    if present == 0:
        status = "ABSENT"
    elif present < 2:
        status = "SKELETON"
    elif present < len(deps):
        status = "PARTIAL"
    else:
        status = "ACTIVE"
    return CoreStatus(
        name="openhands",
        status=status,
        dependencies_resolved=[k for k, v in deps.items() if v in {"importable", "present", "available", "writable"}],
        dependencies_missing=[k for k, v in deps.items() if v in {"missing", "not_writable"}],
        probes=deps,
        notes="OpenHands-style code agent; 4/4 ACTIVE means agent+runtime+node+workspace all resolved",
    )


def probe_superpowers() -> CoreStatus:
    skill_dir = Path.home() / ".hermes" / "skills"
    deps = {
        "skill_dir_present": "present" if skill_dir.exists() else "missing",
        "skill_count": str(len(list(skill_dir.glob("**/SKILL.md")))) if skill_dir.exists() else "0",
        "env_PGG_ARCHON_PROFILE": _probe_env("PGG_ARCHON_PROFILE"),
        "path_~/.hermes/workspace": _probe_path_writable(Path.home() / ".hermes/workspace"),
    }
    present = sum(1 for k, v in deps.items() if (k == "skill_count" and v not in {"0", "0\n"}) or v in {"present", "writable"})
    if deps["skill_dir_present"] == "missing" and deps["env_PGG_ARCHON_PROFILE"] == "missing":
        status = "ABSENT"
    elif present < 2:
        status = "SKELETON"
    elif present < 4:
        status = "PARTIAL"
    else:
        status = "ACTIVE"
    return CoreStatus(
        name="superpowers",
        status=status,
        dependencies_resolved=[k for k, v in deps.items() if v in {"present", "writable"} or (k == "skill_count" and v not in {"0"})],
        dependencies_missing=[k for k, v in deps.items() if v in {"missing", "0"} or (k == "skill_count" and v == "0")],
        probes=deps,
        notes="Super-powers skill composition; 4/4 ACTIVE means skills+profile+workspace all resolved",
    )


PROBES = [probe_evolver, probe_autoresearch, probe_openhands, probe_superpowers]


def run_tiangong() -> dict[str, Any]:
    cores = [probe() for probe in PROBES]
    summary = {
        "schema": "PGGArchonTiangongFourCore/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cores": [asdict(c) for c in cores],
        "active_count": sum(1 for c in cores if c.status == "ACTIVE"),
        "partial_count": sum(1 for c in cores if c.status == "PARTIAL"),
        "skeleton_count": sum(1 for c in cores if c.status == "SKELETON"),
        "absent_count": sum(1 for c in cores if c.status == "ABSENT"),
        "boundary": "status surface of 4 cores; ACTIVE means 4/4 surface gates resolved; not full AGI",
    }
    return summary


if __name__ == "__main__":
    import json
    print(json.dumps(run_tiangong(), ensure_ascii=False, indent=2))
