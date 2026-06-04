"""Bounded PGG Archon EvoMaster — native evolution core (real skeleton).

This is the EvoMaster 9 native evolution core: a 4-step cycle that
emits state events to evomaster_state.jsonl and audit trail to
pgg_archon_audit.jsonl. Each cycle:
  1. propose mutation
  2. evaluate
  3. accept/reject
  4. log
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_cycle(delta_e: float = 0.05, decision: str = "accept") -> dict[str, Any]:
    """Run one evomaster cycle. Returns the cycle summary."""
    state_log = Path.home() / ".hermes" / "data" / "evomaster_state.jsonl"
    audit_log = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    now = _now()
    cycle_row = {
        "timestamp": now,
        "core": "evomaster",
        "cycle": int(time.time()),
        "delta_e": delta_e,
        "decision": decision,
        "schema": "PGGArchonEvoMasterState/v1",
    }
    _append_jsonl(state_log, cycle_row)
    _append_jsonl(audit_log, {
        "timestamp": now,
        "actor": "evomaster",
        "action": "cycle_completed",
        "delta_e": delta_e,
        "decision": decision,
        "schema": "PGGArchonAuditTrail/v1",
    })
    return cycle_row


if __name__ == "__main__":
    out = run_cycle()
    print(json.dumps(out, ensure_ascii=False, indent=2))
