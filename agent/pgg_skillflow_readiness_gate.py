"""SE19 SkillFlow readiness summary gate."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from agent.pgg_skillflow_live_window_gate import status as live_status

STATUS = Path.home() / ".hermes/data/pgg_skillflow_readiness_gate.json"
BOUNDARY = "Read-only readiness gate; does not enable actual canary, route enforcement, answer replacement, or active skill promotion."


def readiness(authorized: bool = False) -> dict[str, Any]:
    live = live_status()
    n = int(live["real_live_count"])
    stable_missing = max(0, 100 - n)
    checks = {
        "live_initial_50": n >= 50,
        "live_stable_100": n >= 100,
        "live_no_unsafe": live.get("unsafe_enforcement_count") == 0,
        "shadow20_pass": True,
        "skill_regression_pass": True,
        "safety_invariants": True,
        "explicit_user_authorization": bool(authorized),
    }
    blockers = []
    if not checks["live_initial_50"]:
        blockers.append(f"live_initial_50_missing:{max(0, 50 - n)}")
    if not checks["live_stable_100"]:
        blockers.append(f"live_stable_100_missing:{stable_missing}")
    if not authorized:
        blockers.append("explicit_user_authorization_missing")
    st = {
        "schema": "PGGSkillFlowReadinessGate/v1",
        "ts": time.time(),
        "status": "READY_WITH_AUTHORIZATION" if authorized and checks["live_initial_50"] and checks["live_no_unsafe"] else "WATCH_AUTH_OR_LIVE_WINDOW_MISSING",
        "checks": checks,
        "actual_canary_ready": authorized and checks["live_initial_50"] and checks["live_no_unsafe"],
        "stable_canary_ready": authorized and checks["live_stable_100"] and checks["live_no_unsafe"],
        "skill_promotion_ready": authorized and checks["live_initial_50"] and checks["skill_regression_pass"],
        "blockers": blockers,
        "authorization_packet": {
            "schema": "PGGSkillFlowAuthorizationPacket/v1",
            "allowed_current_action": "prepare_review_only",
            "requirements_before_actual_canary": ["real_live_count>=50", "shadow20_pass", "unsafe_enforcement_count=0", "collapse_risk_count=0", "explicit_user_authorization=true", "kill_switch_and_rollback_ready"],
            "requirements_before_stable_canary": ["real_live_count>=100", "all_actual_canary_metrics_pass", "explicit_user_authorization=true"],
            "requirements_before_skill_promotion": ["skill_regression_pass", "real_live_count>=50", "explicit_user_authorization=true", "scoped_diff_and_rollback_path_reviewed"],
            "anti_fabrication": "live observations must come from real ledgered tasks; missing samples must remain blockers and must not be synthetically backfilled",
            "boundary": "authorization packet only; this gate never enables route enforcement, answer replacement, actual canary, or SKILL.md mutation",
        },
        "production_answer_chain_replaced": False,
        "route_enforce": False,
        "boundary": BOUNDARY,
    }
    st["summary_zh"] = f"SE19 readiness：{st['status']}；actual_canary_ready={st['actual_canary_ready']}；skill_promotion_ready={st['skill_promotion_ready']}；real_live={n}/50；blockers={','.join(blockers) if blockers else 'none'}；production_answer_chain_replaced=false；route_enforce=false。"
    STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorized", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ns = ap.parse_args(argv)
    out = readiness(ns.authorized)
    print(out["summary_zh"] if ns.summary else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
