"""Bounded PGG Archon Core Cognition Prompt Enforcement — file-21 (real surface).

4-probe status surface for 核心认知 Prompt 强制写入 md 文件:
  1. agent.pgg_archon_core_cognition module is importable
  2. ~/.hermes/data/core_cognition_prompts.jsonl or similar log exists
  3. env PGG_ARCHON_CORE_COGNITION_VERSION is set
  4. ~/.hermes/AGENTS.md is writable (per profile)
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
class CoreCognitionProbe:
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
        test = p / ".pgg_archon_core_cognition_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_core_cognition() -> CoreCognitionProbe:
    log = Path.home() / ".hermes" / "data" / "core_cognition_prompts.jsonl"
    agents_md = Path.home() / ".hermes" / "AGENTS.md"
    deps = {
        "module_core_cognition": _probe_module("agent.pgg_archon_core_cognition"),
        "core_cognition_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_CORE_COGNITION_VERSION": _probe_env("PGG_ARCHON_CORE_COGNITION_VERSION"),
        "AGENTS_md_writable": _probe_path_writable(agents_md.parent),
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
    return CoreCognitionProbe(
        name="core_cognition",
        status=status,
        probes=deps,
        notes=f"Core cognition prompt enforcement super-evolution 21; {present}/4 surface gates resolved",
    )


def run_core_cognition() -> dict[str, Any]:
    p = probe_core_cognition()
    return {
        "schema": "PGGArchonCoreCognition/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_core_cognition(), ensure_ascii=False, indent=2))
