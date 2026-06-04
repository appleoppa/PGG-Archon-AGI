"""Bounded PGG Archon Tiangong (天工) skill — three-core orchestration entrypoint.

This module does NOT replace existing super_evolution_20 / Tiangong four-core logic.
It only provides a thin introspection + status surface so the skill can be invoked
explicitly from the closed-loop pipeline.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

TIANGONG_FOUR_CORE_NAMES = [
    "evolver",
    "autoresearch",
    "openhands",
    "superpowers",
]

EVIDENCE_PATHS = {
    # evolver is a real Rust binary apex13; surface it in the audit
    "evolver": [".hermes/apex-evolution-engine/"],
    # autoresearch is implemented in Python under agent/
    "autoresearch": ["hermes-agent/agent/pgg_archon_regression_generator.py"],
    # openhands is genuinely absent on this machine
    "openhands": [],
    # superpowers is released as the super-evolution-20 skill and the apex-skill wrapper
    "superpowers": ["hermes-agent/skills/workflow/super-evolution-20/", "hermes-agent/skills/workflow/apex-skill/"],
}


@dataclass
class TiangongCoreStatus:
    name: str
    state: str  # present / partial / absent
    evidence: list[str]
    note: str


def _check_evidence(paths: list[str], home: Path) -> list[str]:
    """Check paths relative to $HOME. Supports both real path and absolute path.

    Each `paths` entry may be a relative path (resolved against $HOME) or an
    absolute path. Return the entries that exist on disk.
    """
    found: list[str] = []
    for p in paths:
        if os.path.isabs(p):
            if os.path.exists(p):
                found.append(p)
        else:
            if (home / p).exists():
                found.append(p)
    return found


def collect_tiangong_status(home: Path | None = None) -> dict[str, Any]:
    home = home or Path.home() / ".hermes"
    out: list[TiangongCoreStatus] = []
    for name in TIANGONG_FOUR_CORE_NAMES:
        ev = EVIDENCE_PATHS.get(name, [])
        present = _check_evidence(ev, home)
        if not ev:
            state = "absent"
            note = "no evidence path declared; module absent on this machine"
        elif present:
            state = "present" if len(present) == len(ev) else "partial"
            note = f"{len(present)}/{len(ev)} evidence path(s) found"
        else:
            state = "absent"
            note = "evidence paths declared but none present"
        out.append(TiangongCoreStatus(name=name, state=state, evidence=present, note=note))
    return {
        "schema": "PGGArchonTiangongStatus/v1",
        "cores": [asdict(c) for c in out],
        "summary_state": _summary_state([c.state for c in out]),
    }


def _summary_state(states: list[str]) -> str:
    if all(s == "present" for s in states):
        return "READY"
    if any(s == "present" for s in states):
        return "PARTIAL"
    return "ABSENT"


def write_tiangong_status(path: Path) -> dict[str, Any]:
    data = collect_tiangong_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path.home() / ".hermes/workspace/audit/tiangong_status.json"))
    args = ap.parse_args()
    data = write_tiangong_status(Path(args.out))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
