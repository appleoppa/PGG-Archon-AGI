"""Bounded PGG Archon Fusion — file-17 (real surface).

4-probe status surface for 融合 (fusion: DeepSeek-Reasonix + APEX-SKILL):
  1. agent.pgg_archon_fusion module is importable
  2. ~/.hermes/data/fusion_log.jsonl exists
  3. env PGG_ARCHON_FUSION_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl has ≥1 line
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class FusionProbe:
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


def probe_fusion() -> FusionProbe:
    log = Path.home() / ".hermes" / "data" / "fusion_log.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    audit_lines = sum(1 for _ in audit.open("r", encoding="utf-8")) if audit.exists() else 0
    deps = {
        "module_fusion": _probe_module("agent.pgg_archon_fusion"),
        "fusion_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_FUSION_VERSION": _probe_env("PGG_ARCHON_FUSION_VERSION"),
        "audit_trail_lines": str(audit_lines),
    }
    present = 0
    if deps["module_fusion"] == "importable":
        present += 1
    if deps["fusion_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_FUSION_VERSION"] == "present":
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
    return FusionProbe(
        name="fusion",
        status=status,
        probes=deps,
        notes=f"Fusion super-evolution 17; {present}/4 surface gates resolved",
    )


def run_fusion() -> dict[str, Any]:
    p = probe_fusion()
    return {
        "schema": "PGGArchonFusion/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_fusion(), ensure_ascii=False, indent=2))
