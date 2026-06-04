"""Bounded PGG Archon Deep Self-Evolution — file-3 (real surface).

4-probe status surface for 深度自进化 (deep self-evolution):
  1. agent.pgg_archon_deep_self_evolution module is importable
  2. ~/.hermes/data/deep_self_evolution_log.jsonl exists
  3. env PGG_ARCHON_DEEP_SELF_EVOLUTION_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl has ≥1 line (audit trail signal)
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class DeepSelfEvolutionProbe:
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


def probe_deep_self_evolution() -> DeepSelfEvolutionProbe:
    log = Path.home() / ".hermes" / "data" / "deep_self_evolution_log.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    audit_lines = sum(1 for _ in audit.open("r", encoding="utf-8")) if audit.exists() else 0
    deps = {
        "module_deep_self_evolution": _probe_module("agent.pgg_archon_deep_self_evolution"),
        "deep_self_evolution_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_DEEP_SELF_EVOLUTION_VERSION": _probe_env("PGG_ARCHON_DEEP_SELF_EVOLUTION_VERSION"),
        "audit_trail_lines": str(audit_lines),
    }
    present = 0
    if deps["module_deep_self_evolution"] == "importable":
        present += 1
    if deps["deep_self_evolution_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_DEEP_SELF_EVOLUTION_VERSION"] == "present":
        present += 1
    if audit_lines >= 1:
        present += 1
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return DeepSelfEvolutionProbe(
        name="deep_self_evolution",
        status=status,
        probes=deps,
        notes=f"Deep self-evolution super-evolution 3; {present}/4 surface gates resolved",
    )


def run_deep_self_evolution() -> dict[str, Any]:
    p = probe_deep_self_evolution()
    return {
        "schema": "PGGArchonDeepSelfEvolution/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_deep_self_evolution(), ensure_ascii=False, indent=2))
