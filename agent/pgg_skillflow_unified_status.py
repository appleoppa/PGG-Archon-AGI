"""SE19 SkillFlow unified read-only status.

Aggregates the live-window anti-fabrication gate and readiness gate.  It is a
status surface only: no route enforcement, no answer-chain replacement, no skill
promotion, and no config/credential/scheduler mutation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.pgg_skillflow_live_window_gate import status as live_status
from agent.pgg_skillflow_readiness_gate import readiness

DATA = Path.home() / ".hermes" / "data"
LATEST = DATA / "pgg_skillflow_unified_status_latest.json"
LEDGER = DATA / "pgg_skillflow_unified_status_ledger.jsonl"
BOUNDARY = (
    "Read-only SE19 SkillFlow unified status; does not enable route enforcement, "
    "production answer-chain replacement, actual canary, or SKILL.md mutation."
)


def build_status(*, authorized: bool = True) -> dict[str, Any]:
    live = live_status()
    ready = readiness(authorized=authorized)
    checks = {
        "live_window_stable": str(live.get("status", "")).startswith("PASS_STABLE"),
        "live_window_initial": int(live.get("real_live_count") or 0) >= 50,
        "no_unsafe_enforcement": int(live.get("unsafe_enforcement_count") or 0) == 0,
        "no_collapse_risk": int(live.get("collapse_risk_count") or 0) == 0,
        "readiness_authorized": bool(ready.get("actual_canary_ready")),
        "skill_promotion_ready": bool(ready.get("skill_promotion_ready")),
        "production_answer_chain_replaced_false": live.get("production_answer_chain_replaced") is False and ready.get("production_answer_chain_replaced") is False,
        "route_enforce_false": live.get("route_enforce") is False and ready.get("route_enforce") is False,
    }
    status = "PASS_SKILLFLOW_UNIFIED_STATUS" if all(checks.values()) else "WATCH_SKILLFLOW_UNIFIED_STATUS"
    rec = {
        "schema": "PGGSkillFlowUnifiedStatus/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "live_window": live,
        "readiness": ready,
        "summary_zh": (
            f"SE19 unified：{status}；strict_real_live={live.get('real_live_count')}/100；"
            f"actual_canary_ready={ready.get('actual_canary_ready')}；"
            f"skill_promotion_ready={ready.get('skill_promotion_ready')}；"
            "production_answer_chain_replaced=false；route_enforce=false。"
        ),
        "boundary": BOUNDARY,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--unauthorized", action="store_true", help="show readiness without user authorization")
    args = ap.parse_args(argv)
    rec = build_status(authorized=not args.unauthorized)
    if args.summary:
        print(rec["summary_zh"])
    else:
        print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else rec["summary_zh"])
    return 0 if str(rec.get("status", "")).startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
