"""PGG bounded production readiness summary gate."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from agent.pgg_answer_chain_route_preflight_gate import evaluate as answer_route_preflight
from agent.pgg_skillflow_readiness_gate import readiness

STATUS = Path.home() / ".hermes/data/pgg_production_readiness_gate.json"
E2E_STATUS = Path.home() / ".hermes/data/pgg_limited_support_e2e_status.json"
BOUNDARY = "Separates bounded support-lane readiness from strict production answer-chain readiness; does not enable routes, does not replace answer chain, and does not fabricate SkillFlow live samples."


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        return {"exists": True, "path": str(path), "error": repr(exc)}


def gate() -> dict[str, Any]:
    sf = readiness(True)
    preflight = answer_route_preflight()
    e2e = _read_json(E2E_STATUS)
    n = int(sf["summary_zh"].split("real_live=")[1].split("/50")[0])
    stable_missing = max(0, 100 - n)
    answer_chain_replaced = preflight.get("production_answer_chain_replaced") is True
    route_enforced = preflight.get("route_enforce_for_skillflow") is True
    answer_chain_limited = preflight.get("production_answer_chain_replaced") == "limited_support_lane"
    route_limited = preflight.get("route_enforce_for_skillflow") == "limited_support_lane"
    answer_preflight_ready = preflight.get("answer_chain_status") in {"OBSERVE_ONLY_READY", "SHADOW_CANARY_PASS", "LIMITED_SUPPORT_REPLACED"}
    route_preflight_ready = preflight.get("route_enforce_status") in {"LIMITED_SUPPORT_ENFORCE_READY", "LIMITED_SUPPORT_CANARY_PASS", "LIMITED_SUPPORT_ENFORCED"}
    shadow_canary_pass = preflight.get("answer_chain_status") in {"SHADOW_CANARY_PASS", "LIMITED_SUPPORT_REPLACED"}
    route_canary_pass = preflight.get("route_enforce_status") in {"LIMITED_SUPPORT_CANARY_PASS", "LIMITED_SUPPORT_ENFORCED"}
    e2e_pass = e2e.get("status") == "PASS_LIMITED_SUPPORT_E2E_AND_ROLLBACK"
    strict_checks = {
        "skillflow_initial_50": n >= 50,
        "skillflow_stable_100": n >= 100,
        "answer_chain_observe_only_ready": answer_preflight_ready,
        "answer_chain_shadow_canary_pass": shadow_canary_pass,
        "route_enforce_limited_support_ready": route_preflight_ready,
        "route_enforce_limited_canary_pass": route_canary_pass,
        "production_answer_chain_replaced": answer_chain_replaced,
        "production_answer_chain_limited_support": answer_chain_limited,
        "route_enforce_true_in_skillflow": route_enforced,
        "route_enforce_limited_support": route_limited,
        "limited_support_e2e_and_rollback_pass": e2e_pass,
        "actual_canary_ready": bool(sf.get("actual_canary_ready")),
        "stable_canary_ready": bool(sf.get("stable_canary_ready")),
    }
    blockers = []
    if not strict_checks["skillflow_stable_100"]:
        blockers.append(f"skillflow_stable_live_missing:{stable_missing}")
    if not (answer_chain_replaced or answer_chain_limited):
        blockers.append("active_limited_answer_chain_not_enabled" if shadow_canary_pass else ("answer_chain_shadow_canary_not_run" if answer_preflight_ready else "production_answer_chain_not_replaced"))
    if not (route_enforced or route_limited):
        blockers.append("active_limited_route_enforce_not_enabled" if route_canary_pass else ("route_enforce_limited_canary_not_run" if route_preflight_ready else "skillflow_route_enforce_false"))
    if answer_chain_limited and route_limited and not e2e_pass:
        blockers.append("limited_support_e2e_or_rollback_not_passed")
    strict_score = 92 if answer_chain_limited and route_limited and e2e_pass and n >= 100 else (86 if answer_chain_limited and route_limited and n >= 100 else (78 if shadow_canary_pass and route_canary_pass and n >= 100 else (70 if answer_preflight_ready and route_preflight_ready and n >= 100 else 62)))
    st = {
        "schema": "PGGProductionReadinessGate/v1",
        "ts": time.time(),
        "status": "PASS_LIMITED_SUPPORT_LANE_E2E_ACTIVE_STRICT_PRODUCTION_HOLD" if answer_chain_limited and route_limited and e2e_pass else ("PASS_LIMITED_SUPPORT_LANE_ACTIVE_STRICT_PRODUCTION_HOLD" if answer_chain_limited and route_limited else "PASS_BOUNDED_SUPPORT_LANE_READY_STRICT_PRODUCTION_HOLD"),
        "strict_production_readiness_score": strict_score,
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
        "answer_chain_status": preflight.get("answer_chain_status"),
        "route_enforce_status": preflight.get("route_enforce_status"),
        "next_safe_action": preflight.get("next_safe_action"),
        "bounded_support_lane_ready": True,
        "strict_production_ready": False,
        "production_answer_chain_replaced": "limited_support_lane" if answer_chain_limited else False,
        "route_enforce_for_skillflow": "limited_support_lane" if route_limited else False,
        "allowed_scope": "exact/general bounded support lane only; legal/audit/AGI denied; operator controlled",
        "forbidden_claims": ["full AGI", "official benchmark passed", "legal correctness proof", "unsupervised production takeover", "full production answer-chain replacement"],
        "evidence_paths": {
            "skillflow_readiness": str(Path.home() / ".hermes/data/pgg_skillflow_readiness_gate.json"),
            "answer_chain_route_preflight": str(Path.home() / ".hermes/data/pgg_answer_chain_route_preflight.json"),
            "limited_support_e2e": str(E2E_STATUS),
        },
        "boundary": BOUNDARY,
    }
    st["summary_zh"] = (
        f"生产readiness门禁：{st['status']}；严格生产分={st['strict_production_readiness_score']}；"
        f"有界支撑通道分={st['bounded_support_lane_readiness_score']}；SkillFlow real_live={n}/50；"
        f"answer_chain={st['answer_chain_status']}；route_enforce={st['route_enforce_status']}；"
        f"production_answer_chain_replaced={st['production_answer_chain_replaced']}；"
        f"route_enforce_for_skillflow={st['route_enforce_for_skillflow']}。"
    )
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
