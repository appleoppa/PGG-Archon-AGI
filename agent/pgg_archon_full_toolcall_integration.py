"""Bounded PGG Archon Full Toolcall Integration — file-05.5 (real surface).

4-probe status surface for full-toolcall-integration:
  1. agent/ contains pgg_archon_toolcall* modules
  2. ~/.hermes/logs exists
  3. env PGG_ARCHON_TOOLCALL_VERSION is set
  4. ~/.hermes/workspace is writable
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ToolcallIntegrationProbe:
    name: str
    status: str
    probes: dict[str, str]
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_cli(cli: str) -> str:
    return "available" if shutil.which(cli) else "missing"


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_toolcall_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_toolcall_integration() -> ToolcallIntegrationProbe:
    agent_dir = Path("/Users/appleoppa/.hermes/hermes-agent/agent")
    tc_count = len(list(agent_dir.glob("*toolcall*.py"))) if agent_dir.exists() else 0
    logs_dir = Path.home() / ".hermes" / "logs"
    log_files = list(logs_dir.glob("*")) if logs_dir.exists() else []
    deps = {
        "agent_toolcall_module_count": str(tc_count),
        "log_dir_files": str(len(log_files)),
        "env_PGG_ARCHON_TOOLCALL_VERSION": _probe_env("PGG_ARCHON_TOOLCALL_VERSION"),
        "path_~/.hermes/workspace": _probe_path_writable(Path.home() / ".hermes" / "workspace"),
    }
    present = (
        (1 if tc_count >= 1 else 0)
        + (1 if len(log_files) >= 1 else 0)
        + (1 if deps["env_PGG_ARCHON_TOOLCALL_VERSION"] == "present" else 0)
        + (1 if deps["path_~/.hermes/workspace"] == "writable" else 0)
    )
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return ToolcallIntegrationProbe(
        name="toolcall_integration",
        status=status,
        probes=deps,
        notes=f"Full toolcall integration super-evolution 5.5; {present}/4 surface gates resolved",
    )


def run_toolcall_integration() -> dict[str, Any]:
    p = probe_toolcall_integration()
    return {
        "schema": "PGGArchonFullToolcallIntegration/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_toolcall_integration(), ensure_ascii=False, indent=2))
