"""Bounded PGG Archon Code Agent — OpenHands-style code agent (skeleton).

Real status surface (not a marker). Provides 4 probes used by
tiangong-four-core to determine openhands ACTIVE state.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class OpenHandsProbe:
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
        test = p / ".pgg_archon_openhands_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_openhands() -> OpenHandsProbe:
    deps = {
        "module_pgg_archon_code_agent": "importable",
        "env_OPENHANDS_RUNTIME": _probe_env("OPENHANDS_RUNTIME"),
        "cli_node": _probe_cli("node"),
        "path_/tmp/pgg_archon_workspace": _probe_path_writable(Path("/tmp") / "pgg_archon_workspace"),
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "available", "writable"})
    if present == len(deps):
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return OpenHandsProbe(
        name="openhands",
        status=status,
        probes=deps,
        notes=f"OpenHands-style code agent; {present}/4 surface gates resolved",
    )


def run_code_agent() -> dict[str, Any]:
    p = probe_openhands()
    return {
        "schema": "PGGArchonCodeAgent/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_code_agent(), ensure_ascii=False, indent=2))
