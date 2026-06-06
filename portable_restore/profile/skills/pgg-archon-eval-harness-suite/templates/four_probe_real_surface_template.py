"""Bounded PGG Archon 4-probe real-surface template — copy and customize.

Use this template to create new ABSENT → ACTIVE surfaces for the
33 super-evolution desktop files. The 4 probes are:

  1. _probe_env           — required environment variable present
  2. _probe_python_module — required Python module importable
  3. _probe_cli           — required CLI binary in PATH
  4. _probe_path_writable — required directory writable

Aggregation rule (mimics tiangong-four-core):

  present == 4  →  ACTIVE
  present >= 2  →  PARTIAL
  present >= 1  →  SKELETON
  present == 0  →  ABSENT

Boundary (non-negotiable): this template probes the surface only.
ACTIVATE means all 4 surface gates are resolved at probe time; it
does NOT mean the underlying system is production-ready. Probe-time
state can differ from runtime state.

Customize for your own file by:
  1. Rename CoreStatus fields (name, status) to your subsystem
  2. Fill the deps dict with the 4 specific gates
  3. Add unit tests in tests/test_<name>.py asserting the 4-state machine
  4. Run with the probe env vars set in the test environment
"""

from __future__ import annotations

import importlib
import os
import shutil
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
        test = p / ".pgg_archon_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def aggregate_status(deps: dict[str, str]) -> str:
    """Aggregate 4-probe results into ACTIVE / PARTIAL / SKELETON / ABSENT.

    Rules (mimics tiangong-four-core / apex_engine / code_agent):
      present == len(deps)  →  ACTIVE
      present >= 2           →  PARTIAL
      present >= 1           →  SKELETON
      present == 0           →  ABSENT
    """
    present_values = {"importable", "present", "available", "writable"}
    present = sum(1 for v in deps.values() if v in present_values)
    if present == len(deps):
        return "ACTIVE"
    if present >= 2:
        return "PARTIAL"
    if present >= 1:
        return "SKELETON"
    return "ABSENT"


def make_core_status(name: str, deps: dict[str, str], notes: str = "") -> CoreStatus:
    """Construct a CoreStatus from a deps dict.

    Args:
        name: subsystem identifier
        deps: mapping of gate_name → probe_result_string
        notes: free-form documentation string
    """
    status = aggregate_status(deps)
    resolved = []
    missing = []
    present_values = {"importable", "present", "available", "writable"}
    for k, v in deps.items():
        if v in present_values:
            resolved.append(k)
        else:
            missing.append(k)
    return CoreStatus(
        name=name,
        status=status,
        dependencies_resolved=resolved,
        dependencies_missing=missing,
        probes=deps,
        notes=notes,
    )


def run_summary(cores: list[CoreStatus]) -> dict[str, Any]:
    return {
        "schema": "PGGArchonFourProbeTemplate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cores": [asdict(c) for c in cores],
        "active_count": sum(1 for c in cores if c.status == "ACTIVE"),
        "partial_count": sum(1 for c in cores if c.status == "PARTIAL"),
        "skeleton_count": sum(1 for c in cores if c.status == "SKELETON"),
        "absent_count": sum(1 for c in cores if c.status == "ABSENT"),
        "boundary": "4-probe surface only; ACTIVE means all 4 gates resolved at probe time; not production-ready",
    }


# Example: copy this block and customize for your subsystem
if __name__ == "__main__":
    import json

    EXAMPLE_DEPS = {
        "env_MY_REQUIRED_ENV": _probe_env("MY_REQUIRED_ENV"),
        "module_pgg_archon_my_subsystem": _probe_python_module("agent.pgg_archon_my_subsystem"),
        "cli_my_binary": _probe_cli("my-binary"),
        "path_/tmp/my_workspace": _probe_path_writable(Path("/tmp") / "my_workspace"),
    }
    c = make_core_status(
        "my_subsystem",
        EXAMPLE_DEPS,
        notes="copy this block; replace EXAMPLE_DEPS with the 4 gates you need to verify",
    )
    print(json.dumps(run_summary([c]), ensure_ascii=False, indent=2))
