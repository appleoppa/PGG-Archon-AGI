"""Bounded PGG Archon Book-to-Skill — file-15 (real surface).

4-probe status surface for book-to-skill (parsing books/docs into skills):
  1. agent.pgg_archon_book_to_skill module is importable
  2. ~/.hermes/skills has ≥1 subdirectory (skill outputs)
  3. env PGG_ARCHON_BOOK_TO_SKILL_VERSION is set
  4. ~/.hermes/data/book_to_skill_log.jsonl exists
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class BookToSkillProbe:
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


def probe_book_to_skill() -> BookToSkillProbe:
    log = Path.home() / ".hermes" / "data" / "book_to_skill_log.jsonl"
    skills_dir = Path.home() / ".hermes" / "skills"
    subdirs = [d for d in skills_dir.iterdir() if d.is_dir()] if skills_dir.exists() else []
    deps = {
        "module_book_to_skill": _probe_module("agent.pgg_archon_book_to_skill"),
        "skills_subdir_count": str(len(subdirs)),
        "env_PGG_ARCHON_BOOK_TO_SKILL_VERSION": _probe_env("PGG_ARCHON_BOOK_TO_SKILL_VERSION"),
        "book_to_skill_log_present": "present" if log.exists() else "missing",
    }
    present = 0
    if deps["module_book_to_skill"] == "importable":
        present += 1
    if len(subdirs) >= 1:
        present += 1
    if deps["env_PGG_ARCHON_BOOK_TO_SKILL_VERSION"] == "present":
        present += 1
    if deps["book_to_skill_log_present"] == "present":
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return BookToSkillProbe(
        name="book_to_skill",
        status=status,
        probes=deps,
        notes=f"Book-to-skill super-evolution 15; {present}/4 surface gates resolved",
    )


def run_book_to_skill() -> dict[str, Any]:
    p = probe_book_to_skill()
    return {
        "schema": "PGGArchonBookToSkill/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_book_to_skill(), ensure_ascii=False, indent=2))
