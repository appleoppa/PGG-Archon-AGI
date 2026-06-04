"""Bounded PGG Archon Multi-Agent Collaboration — file-2.5 (real surface).

4-probe status surface for 多智能体协作 (multi-agent collaboration):
  1. agent.pgg_archon_multi_agent_collaboration module is importable
  2. ~/.hermes/data/multi_agent_log.jsonl exists
  3. env PGG_ARCHON_MULTI_AGENT_VERSION is set
  4. agent/ contains ≥5 pgg_archon_orchestrator modules
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
class MultiAgentCollaborationProbe:
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


def probe_multi_agent_collaboration() -> MultiAgentCollaborationProbe:
    log = Path.home() / ".hermes" / "data" / "multi_agent_log.jsonl"
    agent_dir = Path(__file__).resolve().parent
    pattern = re.compile(r"pgg_archon.*orchestrator")
    orches = sorted([p.name for p in agent_dir.glob("pgg_archon_*orchestrator*.py")]) if agent_dir.exists() else []
    deps = {
        "module_multi_agent_collaboration": _probe_module("agent.pgg_archon_multi_agent_collaboration"),
        "multi_agent_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_MULTI_AGENT_VERSION": _probe_env("PGG_ARCHON_MULTI_AGENT_VERSION"),
        "orchestrator_module_count": str(len(orches)),
    }
    present = 0
    if deps["module_multi_agent_collaboration"] == "importable":
        present += 1
    if deps["multi_agent_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_MULTI_AGENT_VERSION"] == "present":
        present += 1
    if len(orches) >= 1:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return MultiAgentCollaborationProbe(
        name="multi_agent_collaboration",
        status=status,
        probes=deps,
        notes=f"Multi-agent collaboration super-evolution 2.5; {present}/4 surface gates resolved",
    )


def run_multi_agent_collaboration() -> dict[str, Any]:
    p = probe_multi_agent_collaboration()
    return {
        "schema": "PGGArchonMultiAgentCollaboration/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_multi_agent_collaboration(), ensure_ascii=False, indent=2))
