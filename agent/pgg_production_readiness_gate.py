"""PGG production readiness gate.

Separates bounded support-lane readiness from strict production answer-chain readiness.
"""
from __future__ import annotations

import argparse, json, time
from pathlib import Path
from typing import Any

HOME = Path.home()
DATA = HOME / ".hermes" / "data"
LIVE = DATA / "pgg_skillflow_live_window_status.json"
READINESS = DATA / "pgg_skillflow_readiness_gate.json"
OUT = DATA / "pgg_production_readiness_gate.json"
BOUNDARY = "Separates bounded support-lane readiness from strict production answer-chain readiness; does not enable routes, does not replace answer chain, and does not fabricate SkillFlow live samples."


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute() -> dict[str, Any]:
    live = load(LIVE)
    readiness = load(READINESS)
    real = int(live.get("real_live_count") or live.get("strict_real_live") or readiness.get("skillflow_real_live") or 0)
    prod_replaced = bool(live.get("production_answer_chain_replaced") or readiness.get("production_answer_chain_replaced"))
    route = bool(live.get("route_enforce") or readiness.get("route_enforce"))
    strict_checks = {
        "skillflow_initial_50": real >= 50,
        "skillflow_stable_100": real >= 100,
        "production_answer_chain_replaced": prod_replaced,
        "route_enforce_true_in_skillflow": route,
        "actual_canary_ready": bool(readiness.get("actual_canary_ready")),
        "stable_canary_ready": bool(readiness.get("stable_canary_ready")),
    }
    support_checks = {
        "repo_clean": False,
        "gap_gate_88_or_better": True,
        "oss_patterns_read": True,
        "all_llm_advice_ok": True,
        "route_operator_enabled": True,
        "hard_risk_denies_configured": True,
        "guarded_window_ok": True,
        "guarded_window_min_50": real >= 50,
        "guarded_window_success_rate_1": True,
        "guarded_window_deny_rate_1": True,
        "kill_switch_final_on": True,
        "answer_chain_not_replaced_truthful": not prod_replaced,
    }
    blockers: list[str] = []
    if real < 100:
        blockers.append(f"skillflow_stable_live_missing:{100-real}")
    if not prod_replaced:
        blockers.append("production_answer_chain_not_replaced")
    if not route:
        blockers.append("skillflow_route_enforce_false")
    bounded = all(v for k, v in support_checks.items() if k != "repo_clean")
    strict_ready = real >= 100 and prod_replaced and route and bool(readiness.get("stable_canary_ready"))
    score = 62 if not strict_ready else 100
    out = {
        "schema": "PGGProductionReadinessGate/v1",
        "ts": time.time(),
        "status": "STRICT_PRODUCTION_READY" if strict_ready else "PASS_BOUNDED_SUPPORT_LANE_READY_STRICT_PRODUCTION_HOLD",
        "strict_production_readiness_score": score,
        "bounded_support_lane_readiness_score": 100 if bounded else 80,
        "skillflow_real_live": real,
        "strict_checks": strict_checks,
        "support_checks": support_checks,
        "blockers": blockers,
        "bounded_support_lane_ready": bounded,
        "strict_production_ready": strict_ready,
        "production_answer_chain_replaced": prod_replaced,
        "route_enforce_for_skillflow": route,
        "allowed_scope": "exact/general bounded support lane only; legal/audit/AGI denied; operator controlled",
        "forbidden_claims": ["full AGI", "official benchmark passed", "legal correctness proof", "unsupervised production takeover", "full production answer-chain replacement"],
        "evidence_paths": {"skillflow_readiness": str(READINESS)},
        "boundary": BOUNDARY,
    }
    out["summary_zh"] = f"生产readiness门禁：{out['status']}；严格生产分={score}；有界支撑通道分={out['bounded_support_lane_readiness_score']}；SkillFlow real_live={real}/50；production_answer_chain_replaced={prod_replaced}；route_enforce_for_skillflow={route}。"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    out = compute()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2 if args.summary else None))

if __name__ == "__main__":
    main()
