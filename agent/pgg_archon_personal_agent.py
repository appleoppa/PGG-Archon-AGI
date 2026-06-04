"""Bounded PGG Archon Personal Agent — file-8 (real surface).

4-probe status surface for 个人智能体 (personal agent):
  1. agent.pgg_archon_personal_agent module is importable
  2. ~/.hermes/data/personal_agent_log.jsonl exists
  3. env PGG_ARCHON_PERSONAL_AGENT_VERSION is set
  4. ~/.hermes/USER.md is writable
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PersonalAgentProbe:
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
        test = p / ".pgg_archon_personal_agent_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_personal_agent() -> PersonalAgentProbe:
    log = Path.home() / ".hermes" / "data" / "personal_agent_log.jsonl"
    user_md = Path.home() / ".hermes" / "USER.md"
    deps = {
        "module_personal_agent": _probe_module("agent.pgg_archon_personal_agent"),
        "personal_agent_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_PERSONAL_AGENT_VERSION": _probe_env("PGG_ARCHON_PERSONAL_AGENT_VERSION"),
        "USER_md_writable": _probe_path_writable(user_md.parent),
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
    return PersonalAgentProbe(
        name="personal_agent",
        status=status,
        probes=deps,
        notes=f"Personal agent super-evolution 8; {present}/4 surface gates resolved",
    )


def run_personal_agent() -> dict[str, Any]:
    p = probe_personal_agent()
    return {
        "schema": "PGGArchonPersonalAgent/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_personal_agent(), ensure_ascii=False, indent=2))
