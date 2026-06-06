"""4-probe real-surface template for PGG Archon subsystem landing.

Drop this into agent/pgg_archon_<your_subsystem>.py and replace EXAMPLE_DEPS
with the 4 gates your subsystem actually depends on. The 4 standard gates are
env / module / cli / path, but you can substitute any 4 deterministic signals
that prove the subsystem is "actually present" vs "declared present".

Real landings using this template (2026-06-04):
  - file-04 context_learning       -> PARTIAL 3/4
  - file-05 memory_system          -> PARTIAL 2/4
  - file-06 token_hygiene          -> ACTIVE 4/4
  - file-5.5 full_toolcall_integ.. -> ACTIVE 4/4
  - file-11 tiangong-four-core     -> ACTIVE 3/4 (autoresearch PARTIAL)
  - file-13 apex-skill             -> ACTIVE 4/4
  - file-24 llm-mutual-constraint  -> ACTIVE 4/4 OK (different pattern)
"""

from __future__ import annotations

import importlib
import os
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# --- 4 standard probes (replace with your subsystem's gates) ---

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
        test = p / ".pgg_archon_<your_subsystem>_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


# --- Status surface dataclass ---

@dataclass
class SubsystemStatus:
    name: str
    status: str  # ABSENT | SKELETON | PARTIAL | ACTIVE
    dependencies_resolved: list[str] = field(default_factory=list)
    dependencies_missing: list[str] = field(default_factory=list)
    probes: dict[str, str] = field(default_factory=dict)
    notes: str = ""


# --- Aggregate state machine ---

def aggregate_status(probes: dict[str, str]) -> str:
    """Map probe results to ACTIVE/PARTIAL/SKELETON/ABSENT.

    - ACTIVE:   all 4 gates resolved
    - PARTIAL:  2 or 3 of 4 gates resolved
    - SKELETON: exactly 1 of 4 gates resolved
    - ABSENT:   0 of 4 gates resolved
    """
    present = sum(1 for v in probes.values() if v in {"importable", "present", "available", "writable"})
    if present == len(probes):
        return "ACTIVE"
    elif present >= 2:
        return "PARTIAL"
    elif present >= 1:
        return "SKELETON"
    else:
        return "ABSENT"


# --- EXAMPLE: replace with your subsystem's 4 gates ---

def probe_<your_subsystem>() -> SubsystemStatus:
    deps = {
        "env_<YOUR_ENV_VAR>": _probe_env("<YOUR_ENV_VAR>"),
        "module_<your_module_path>": _probe_python_module("agent.pgg_archon_<your_module>"),
        "cli_<your_cli>": _probe_cli("<your_cli>"),
        "path_<your_path>": _probe_path_writable(Path.home() / ".hermes/<your_path>"),
    }
    return SubsystemStatus(
        name="<your_subsystem>",
        status=aggregate_status(deps),
        dependencies_resolved=[k for k, v in deps.items() if v in {"importable", "present", "available", "writable"}],
        dependencies_missing=[k for k, v in deps.items() if v in {"missing", "not_writable"}],
        probes=deps,
        notes="<your subsystem> status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    )


# --- Run entrypoint ---

def run_<your_subsystem>() -> dict[str, Any]:
    s = probe_<your_subsystem>()
    return {
        "schema": "PGGArchon<YourSubsystem>/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "subsystem": asdict(s),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_<your_subsystem>(), ensure_ascii=False, indent=2))
