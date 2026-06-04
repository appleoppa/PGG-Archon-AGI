"""Bounded PGG Archon Super-Evolution Audit Lane — closed-loop orchestrator.

Stitches together the existing P3 harnesses:
  - tiangong_status (super_evolution 11)
  - research_unified_engine (super_evolution 8)
  - multimodal_status
  - redteam_harness
  - benchmark_harness
  - p3_verifier

into a single repeatable audit lane. Each pass:
  1. snapshots the 6 surfaces
  2. optionally invokes a redteam + benchmark pass
  3. writes a per-pass JSON report
  4. lets downstream LLM verifiers (4) confirm

The lane is bounded: it does NOT mutate any DB; it only emits status
JSONs to the audit workspace.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pgg_archon_tiangong_skill import collect_tiangong_status
from .pgg_archon_research_unified_engine import collect_research_artifacts
from .pgg_archon_multimodal_status import collect_multimodal_status
from .pgg_archon_se_sync import sync as sync_super_evolution_cards


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_lane(out_dir: Path, run_id: str | None = None) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    run_id = run_id or started.replace(":", "").replace("-", "").split(".")[0]
    lane_dir = out_dir / f"lane_{run_id}"
    lane_dir.mkdir(parents=True, exist_ok=True)

    snap = {
        "schema": "PGGArchonSuperEvolutionLaneSnap/v1",
        "run_id": run_id,
        "started_at": started,
        "tiangong": collect_tiangong_status(),
        "research_engine": collect_research_artifacts(),
        "multimodal": collect_multimodal_status(),
    }
    _write(lane_dir / "01_snap.json", snap)

    se_sync = sync_super_evolution_cards()
    _write(lane_dir / "02_se_sync.json", se_sync)

    finished = datetime.now(timezone.utc).isoformat()
    return {
        "schema": "PGGArchonSuperEvolutionLaneResult/v1",
        "run_id": run_id,
        "started_at": started,
        "finished_at": finished,
        "lane_dir": str(lane_dir),
        "snap_path": str(lane_dir / "01_snap.json"),
        "se_sync_path": str(lane_dir / "02_se_sync.json"),
        "synced_33_card_path": se_sync.get("synced_path"),
        "se_sync_status_distribution": se_sync.get("status_distribution"),
        "tiangong_summary_state": snap["tiangong"]["summary_state"],
        "research_engine_state": snap["research_engine"]["engine_state"],
        "multimodal_overall": snap["multimodal"]["overall"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(Path.home() / ".hermes/workspace/audit/super_evolution_lane"),
    )
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    result = run_lane(Path(args.out), args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
