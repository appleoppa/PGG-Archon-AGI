"""Bounded PGG Archon Context Formula — file-4.5 (real surface).

4-probe status surface for 上下文公式 (context formula):
  1. agent.pgg_archon_context_formula module is importable
  2. ~/.hermes/data/context_formula_log.jsonl exists
  3. env PGG_ARCHON_CONTEXT_FORMULA_VERSION is set
  4. ~/.hermes/memories/MEMORY.md is present

Also houses build_context_formula_report() and build_context_budget_policy()
for tools.pgg_archon_tools import compatibility.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ContextFormulaProbe:
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


def probe_context_formula() -> ContextFormulaProbe:
    log = Path.home() / ".hermes" / "data" / "context_formula_log.jsonl"
    mem_md = Path.home() / ".hermes" / "memories" / "MEMORY.md"
    deps = {
        "module_context_formula": _probe_module("agent.pgg_archon_context_formula"),
        "context_formula_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_CONTEXT_FORMULA_VERSION": _probe_env("PGG_ARCHON_CONTEXT_FORMULA_VERSION"),
        "MEMORY_md_present": "present" if mem_md.exists() else "missing",
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
    return ContextFormulaProbe(
        name="context_formula",
        status=status,
        probes=deps,
        notes=f"Context formula super-evolution 4.5; {present}/4 surface gates resolved",
    )


def run_context_formula() -> dict[str, Any]:
    p = probe_context_formula()
    return {
        "schema": "PGGArchonContextFormula/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


def build_context_formula_report(
    signals: dict[str, Any] | None = None,
    delta_signals: dict[str, Any] | None = None,
    source: str = "hermes_tool:pgg_ultimate_evolution:context_formula",
) -> dict[str, Any]:
    """Build a bounded context formula report.

    Read-only APEX_MAX context efficiency score.
    Accepts optional context signals, returns structured JSON report.
    """
    if signals is None:
        signals = {}
    return {
        "schema": "PGGArchonContextFormula/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "omega_a": signals.get("omega_a", 1.0),
        "token_savings": signals.get("token_savings", 0),
        "efficiency": signals.get("efficiency", 0.0),
        "accuracy": signals.get("accuracy", 0.0),
        "completeness": signals.get("completeness", 0.0),
        "logic_flow": signals.get("logic_flow", 0.0),
        "response_speed": signals.get("response_speed", 0.0),
        "boundary": "read-only context formula report; not full AGI",
    }


def build_context_budget_policy(
    report: dict[str, Any],
) -> dict[str, Any]:
    """Build a concrete token/tool/skill budget policy from a context formula report.

    Read-only; returns budget recommendations without modifying any config.
    """
    return {
        "schema": "PGGArchonContextBudgetPolicy/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": report.get("source", "hermes_tool:pgg_ultimate_evolution:context_budget_policy"),
        "max_context_tokens": 128000,
        "compression_threshold": 0.85,
        "tool_budget": 90,
        "skill_depth_limit": 3,
        "boundary": "read-only budget policy; does not modify config",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_context_formula(), ensure_ascii=False, indent=2))
