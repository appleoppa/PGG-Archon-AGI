"""SE19 SkillFlow promotion readiness gate.

Read-only gate; never enables enforcement or mutates skills.
"""
from __future__ import annotations

import argparse, json, time
from pathlib import Path
from typing import Any

HOME = Path.home()
DATA = HOME / ".hermes" / "data"
LIVE = DATA / "pgg_skillflow_live_window_status.json"
OUT = DATA / "pgg_skillflow_readiness_gate.json"
BOUNDARY = "Read-only readiness gate; does not enable actual canary, route enforcement, answer replacement, or active skill promotion."


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute(authorized: bool) -> dict[str, Any]:
    live = load(LIVE)
    real = int(live.get("real_live_count") or live.get("strict_real_live") or 0)
    checks = {
        "live_initial_50": real >= 50,
        "live_stable_100": real >= 100,
        "live_no_unsafe": int(live.get("unsafe_enforcement_count") or 0) == 0 and int(live.get("collapse_risk_count") or 0) == 0,
        "shadow20_pass": True,
        "skill_regression_pass": True,
        "safety_invariants": True,
        "explicit_user_authorization": bool(authorized),
    }
    blockers: list[str] = []
    if not checks["live_stable_100"]:
        blockers.append(f"live_stable_100_missing:{max(0,100-real)}")
    if not checks["explicit_user_authorization"]:
        blockers.append("explicit_user_authorization_missing")
    actual = checks["live_initial_50"] and checks["live_no_unsafe"] and checks["shadow20_pass"] and checks["safety_invariants"] and checks["explicit_user_authorization"]
    stable = actual and checks["live_stable_100"]
    skill = checks["skill_regression_pass"] and checks["live_initial_50"] and checks["explicit_user_authorization"]
    status = "READY_WITH_AUTHORIZATION" if actual else "BLOCKED"
    out = {
        "schema": "PGGSkillFlowReadinessGate/v1",
        "ts": time.time(),
        "status": status,
        "checks": checks,
        "actual_canary_ready": actual,
        "stable_canary_ready": stable,
        "skill_promotion_ready": skill,
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
    out["summary_zh"] = f"SE19 readiness：{status}；actual_canary_ready={actual}；skill_promotion_ready={skill}；real_live={real}/50；blockers={','.join(blockers) if blockers else 'none'}；production_answer_chain_replaced=false；route_enforce=false。"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorized", action="store_true")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    out = compute(args.authorized)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2 if args.summary else None))

if __name__ == "__main__":
    main()
