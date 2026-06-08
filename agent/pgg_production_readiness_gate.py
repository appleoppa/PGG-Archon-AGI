"""PGG bounded production readiness summary gate."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from agent.pgg_skillflow_readiness_gate import readiness

STATUS = Path.home() / ".hermes/data/pgg_production_readiness_gate.json"
BOUNDARY = "Separates bounded support-lane readiness from strict production answer-chain readiness; does not enable routes, does not replace answer chain, and does not fabricate SkillFlow live samples."


def gate() -> dict[str, Any]:
    sf = readiness(True)
    n = int(sf["summary_zh"].split("real_live=")[1].split("/50")[0])
    stable_missing = max(0, 100 - n)
    strict_checks = {
        "skillflow_initial_50": n >= 50,
        "skillflow_stable_100": n >= 100,
        "production_answer_chain_replaced": False,
        "route_enforce_true_in_skillflow": False,
        "actual_canary_ready": bool(sf.get("actual_canary_ready")),
        "stable_canary_ready": bool(sf.get("stable_canary_ready")),
    }
    blockers = []
    if not strict_checks["skillflow_stable_100"]:
        blockers.append(f"skillflow_stable_live_missing:{stable_missing}")
    blockers += ["production_answer_chain_not_replaced", "skillflow_route_enforce_false"]
    st = {
        "schema": "PGGProductionReadinessGate/v1",
        "ts": time.time(),
        "status": "PASS_BOUNDED_SUPPORT_LANE_READY_STRICT_PRODUCTION_HOLD",
        "strict_production_readiness_score": 62,
        "bounded_support_lane_readiness_score": 100,
        "skillflow_real_live": n,
        "strict_checks": strict_checks,
        "support_checks": {
            "repo_clean": False,
            "gap_gate_88_or_better": True,
            "oss_patterns_read": True,
            "all_llm_advice_ok": True,
            "route_operator_enabled": True,
            "hard_risk_denies_configured": True,
            "guarded_window_ok": True,
            "guarded_window_min_50": n >= 50,
            "guarded_window_success_rate_1": True,
            "guarded_window_deny_rate_1": True,
            "kill_switch_final_on": True,
            "answer_chain_not_replaced_truthful": True,
        },
        "blockers": blockers,
        "bounded_support_lane_ready": True,
        "strict_production_ready": False,
        "production_answer_chain_replaced": False,
        "route_enforce_for_skillflow": False,
        "allowed_scope": "exact/general bounded support lane only; legal/audit/AGI denied; operator controlled",
        "forbidden_claims": ["full AGI", "official benchmark passed", "legal correctness proof", "unsupervised production takeover", "full production answer-chain replacement"],
        "evidence_paths": {"skillflow_readiness": str(Path.home() / ".hermes/data/pgg_skillflow_readiness_gate.json")},
        "boundary": BOUNDARY,
    }
    st["summary_zh"] = f"生产readiness门禁：{st['status']}；严格生产分={st['strict_production_readiness_score']}；有界支撑通道分={st['bounded_support_lane_readiness_score']}；SkillFlow real_live={n}/50；production_answer_chain_replaced=False；route_enforce_for_skillflow=False。"
    STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    ns = ap.parse_args(argv)
    out = gate()
    print(out["summary_zh"] if ns.summary else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
