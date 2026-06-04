"""Bounded PGG Archon Super Routing — file-10 (real surface).

4-probe status surface for 超级路由 (super routing / channel multiplexing):
  1. agent.pgg_archon_super_routing module is importable
  2. ~/.hermes/data/super_routing_log.jsonl exists
  3. env PGG_ARCHON_SUPER_ROUTING_VERSION is set
  4. ~/.hermes/data/pgg-background-evolution has at least 1 file (routing foundation)
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SuperRoutingProbe:
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
        test = p / ".pgg_archon_super_routing_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_super_routing() -> SuperRoutingProbe:
    log = Path.home() / ".hermes" / "data" / "super_routing_log.jsonl"
    bg_evo = Path.home() / ".hermes" / "data" / "pgg-background-evolution"
    bg_files = list(bg_evo.glob("*")) if bg_evo.exists() else []
    deps = {
        "module_super_routing": _probe_module("agent.pgg_archon_super_routing"),
        "super_routing_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_SUPER_ROUTING_VERSION": _probe_env("PGG_ARCHON_SUPER_ROUTING_VERSION"),
        "pgg_background_evolution_files": str(len(bg_files)),
    }
    present = 0
    if deps["module_super_routing"] == "importable":
        present += 1
    if deps["super_routing_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_SUPER_ROUTING_VERSION"] == "present":
        present += 1
    if len(bg_files) >= 1:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return SuperRoutingProbe(
        name="super_routing",
        status=status,
        probes=deps,
        notes=f"Super routing super-evolution 10; {present}/4 surface gates resolved",
    )


def run_super_routing() -> dict[str, Any]:
    p = probe_super_routing()
    return {
        "schema": "PGGArchonSuperRouting/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_super_routing(), ensure_ascii=False, indent=2))
