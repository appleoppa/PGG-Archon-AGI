"""Bounded PGG Archon Apex-Skill — v0.1.1 skill release layer (real surface).

Maps super-evolution file 13 (APEX-SKILL) to a real status surface with
4 probes:

  1. agent/ contains pgg_archon_* modules (≥ 20)
  2. ~/.hermes/skills/ contains ≥ 100 SKILL.md
  3. env APEX_SKILL_VERSION is set
  4. ~/.hermes/data/ is writable

The status surface returns ACTIVE / PARTIAL / SKELETON / ABSENT based on
how many probes are satisfied.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ApexSkillProbe:
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
        test = p / ".pgg_archon_apex_skill_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_apex_skill() -> ApexSkillProbe:
    agent_dir = Path("/Users/appleoppa/.hermes/hermes-agent/agent")
    skill_dir = Path.home() / ".hermes" / "skills"
    pgg_count = len(list(agent_dir.glob("pgg_archon_*.py"))) if agent_dir.exists() else 0
    skill_count = len(list(skill_dir.glob("**/SKILL.md"))) if skill_dir.exists() else 0
    deps = {
        "agent_pgg_archon_count": str(pgg_count),
        "skill_count": str(skill_count),
        "env_APEX_SKILL_VERSION": _probe_env("APEX_SKILL_VERSION"),
        "path_~/.hermes/data": _probe_path_writable(Path.home() / ".hermes/data"),
    }
    present = (
        (1 if pgg_count >= 20 else 0)
        + (1 if skill_count >= 100 else 0)
        + (1 if deps["env_APEX_SKILL_VERSION"] == "present" else 0)
        + (1 if deps["path_~/.hermes/data"] == "writable" else 0)
    )
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return ApexSkillProbe(
        name="apex_skill",
        status=status,
        probes=deps,
        notes=f"APEX-SKILL v0.1.1 release layer; {present}/4 surface gates resolved",
    )


def run_apex_skill() -> dict[str, Any]:
    p = probe_apex_skill()
    return {
        "schema": "PGGArchonApexSkill/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 surface gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_apex_skill(), ensure_ascii=False, indent=2))
