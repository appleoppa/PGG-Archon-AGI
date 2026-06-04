"""Bounded PGG Archon Quantum Channel Router — file-01 (real surface).

4-probe status surface for 河图洛书 LLM routing:
  1. agent.pgg_archon_quantum_channel_router module is importable
  2. ~/.hermes/data/quantum_router_cache has at least 1 file
  3. env PGG_ARCHON_ROUTER_VERSION is set
  4. ~/.hermes/data/router_health.jsonl or similar router log exists
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
class QuantumChannelRouterProbe:
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
        test = p / ".pgg_archon_router_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_quantum_channel_router() -> QuantumChannelRouterProbe:
    cache_dir = Path.home() / ".hermes" / "data" / "quantum_router_cache"
    health_log = Path.home() / ".hermes" / "data" / "router_health.jsonl"
    cache_files = list(cache_dir.glob("*")) if cache_dir.exists() else []
    deps = {
        "module_quantum_channel_router": _probe_module("agent.pgg_archon_quantum_channel_router"),
        "router_cache_files": str(len(cache_files)),
        "env_PGG_ARCHON_ROUTER_VERSION": _probe_env("PGG_ARCHON_ROUTER_VERSION"),
        "router_health_log": "present" if health_log.exists() else "missing",
    }
    present = (
        (1 if deps["module_quantum_channel_router"] == "importable" else 0)
        + (1 if len(cache_files) >= 1 else 0)
        + (1 if deps["env_PGG_ARCHON_ROUTER_VERSION"] == "present" else 0)
        + (1 if deps["router_health_log"] == "present" else 0)
    )
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return QuantumChannelRouterProbe(
        name="quantum_channel_router",
        status=status,
        probes=deps,
        notes=f"Quantum channel router super-evolution 1; {present}/4 surface gates resolved",
    )


def run_quantum_channel_router() -> dict[str, Any]:
    p = probe_quantum_channel_router()
    return {
        "schema": "PGGArchonQuantumChannelRouter/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_quantum_channel_router(), ensure_ascii=False, indent=2))
