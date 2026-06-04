"""Bounded PGG Archon Research Unified Engine — file-7 (real surface).

4-probe status surface for 科研统一引擎 (research unified engine):
  1. agent.pgg_archon_research_engine module is importable
  2. ~/.hermes/data/research_engine_log.jsonl exists
  3. env PGG_ARCHON_RESEARCH_ENGINE_VERSION is set
  4. ~/.hermes/data/arxiv_papers.jsonl or similar research artifact exists
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ResearchEngineProbe:
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


def probe_research_engine() -> ResearchEngineProbe:
    log = Path.home() / ".hermes" / "data" / "research_engine_log.jsonl"
    arxiv_papers = Path.home() / ".hermes" / "data" / "arxiv_papers.jsonl"
    deps = {
        "module_research_engine": _probe_module("agent.pgg_archon_research_engine"),
        "research_engine_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_RESEARCH_ENGINE_VERSION": _probe_env("PGG_ARCHON_RESEARCH_ENGINE_VERSION"),
        "arxiv_papers_present": "present" if arxiv_papers.exists() else "missing",
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
    return ResearchEngineProbe(
        name="research_engine",
        status=status,
        probes=deps,
        notes=f"Research unified engine super-evolution 7; {present}/4 surface gates resolved",
    )


def run_research_engine() -> dict[str, Any]:
    p = probe_research_engine()
    return {
        "schema": "PGGArchonResearchEngine/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_research_engine(), ensure_ascii=False, indent=2))
