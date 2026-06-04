"""Bounded PGG Archon LLM Coordination — file-2 (real surface).

4-probe status surface for llm 协调 (LLM coordination pattern):
  1. agent.pgg_archon_llm_coordination module is importable
  2. ~/.hermes/data/llm_coordination_log.jsonl exists
  3. env PGG_ARCHON_LLM_COORDINATION_VERSION is set
  4. ~/.hermes/config.yaml has custom_providers with ≥3 entries
"""

from __future__ import annotations

import importlib
import os
import shutil
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class LLMCoordinationProbe:
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
        test = p / ".pgg_archon_llmcoord_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_llm_coordination() -> LLMCoordinationProbe:
    log = Path.home() / ".hermes" / "data" / "llm_coordination_log.jsonl"
    cfg = Path.home() / ".hermes" / "config.yaml"
    provider_count = 0
    if cfg.exists():
        try:
            data = yaml.safe_load(cfg.read_text(errors="replace"))
            if isinstance(data, dict):
                providers = data.get("custom_providers", [])
                if isinstance(providers, list):
                    provider_count = len(providers)
        except Exception:
            pass
    deps = {
        "module_llm_coordination": _probe_module("agent.pgg_archon_llm_coordination"),
        "llm_coordination_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_LLM_COORDINATION_VERSION": _probe_env("PGG_ARCHON_LLM_COORDINATION_VERSION"),
        "custom_providers_count": str(provider_count),
    }
    present = 0
    if deps["module_llm_coordination"] == "importable":
        present += 1
    if deps["llm_coordination_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_LLM_COORDINATION_VERSION"] == "present":
        present += 1
    if provider_count >= 3:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return LLMCoordinationProbe(
        name="llm_coordination",
        status=status,
        probes=deps,
        notes=f"LLM coordination super-evolution 2; {present}/4 surface gates resolved",
    )


def run_llm_coordination() -> dict[str, Any]:
    p = probe_llm_coordination()
    return {
        "schema": "PGGArchonLLMCoordination/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_llm_coordination(), ensure_ascii=False, indent=2))
