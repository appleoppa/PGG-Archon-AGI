"""Bounded PGG Archon Evolution Core Driver — file-16.5 (real surface).

4-probe status surface for pgg-archon-evomap-toolchain (evolver / autoresearch / superpowers / openhands driver):
  1. agent.pgg_archon_evomap_toolchain module is importable
  2. env PGG_ARCHON_EVOMAP_VERSION is set
  3. ~/.hermes/data/evomap_toolchain.jsonl exists
  4. ~/.hermes/workspace is writable
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
class EvomapToolchainProbe:
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
        test = p / ".pgg_archon_evomap_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_evomap_toolchain() -> EvomapToolchainProbe:
    evo_log = Path.home() / ".hermes" / "data" / "evomap_toolchain.jsonl"
    deps = {
        "module_evomap_toolchain": _probe_module("agent.pgg_archon_evomap_toolchain"),
        "env_PGG_ARCHON_EVOMAP_VERSION": _probe_env("PGG_ARCHON_EVOMAP_VERSION"),
        "evomap_log_present": "present" if evo_log.exists() else "missing",
        "path_~/.hermes/workspace": _probe_path_writable(Path.home() / ".hermes" / "workspace"),
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
    return EvomapToolchainProbe(
        name="evomap_toolchain",
        status=status,
        probes=deps,
        notes=f"Evolution core driver evomap-toolchain super-evolution 16.5; {present}/4 surface gates resolved",
    )


def run_evomap_toolchain() -> dict[str, Any]:
    p = probe_evomap_toolchain()
    return {
        "schema": "PGGArchonEvomapToolchain/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_evomap_toolchain(), ensure_ascii=False, indent=2))
