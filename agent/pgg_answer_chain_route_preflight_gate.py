"""PGG answer-chain replacement and SkillFlow route-enforce preflight gate.

This gate is intentionally read-only: it never enables route enforcement and never
marks the production answer-chain as replaced. It turns the two production
blockers into staged, auditable states so later canaries can promote safely.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

STATUS = Path.home() / ".hermes/data/pgg_answer_chain_route_preflight.json"
LIVE = Path.home() / ".hermes/data/pgg_skillflow_live_window_status.json"
READINESS = Path.home() / ".hermes/data/pgg_skillflow_readiness_gate.json"
PROD = Path.home() / ".hermes/data/pgg_production_readiness_gate.json"
SWITCH = Path.home() / ".hermes/data/omniroute_v81_production_switch.json"
ROUTE_CANARY = Path.home() / ".hermes/data/omniroute_route_enforce_canary.json"
CANARY_STATUS = Path.home() / ".hermes/data/pgg_answer_chain_route_canary_status.json"
ACTIVATION_STATUS = Path.home() / ".hermes/data/pgg_limited_support_activation_status.json"
BOUNDARY = "Read-only preflight; does not enable route_enforce, does not replace production answer-chain."
HARD_DENIED = {"chinese_legal", "audit_judge", "agi_architecture_coding"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    try:
        out = json.loads(path.read_text(encoding="utf-8"))
        out.setdefault("path", str(path))
        out["exists"] = True
        return out
    except Exception as exc:  # pragma: no cover - defensive
        return {"exists": True, "path": str(path), "error": repr(exc)}


def evaluate() -> dict[str, Any]:
    live = _read_json(LIVE)
    ready = _read_json(READINESS)
    prod = _read_json(PROD)
    switch = _read_json(SWITCH)
    canary = _read_json(ROUTE_CANARY)
    canary_status = _read_json(CANARY_STATUS)
    activation = _read_json(ACTIVATION_STATUS)

    strict_100 = int(live.get("real_live_count") or 0) >= 100 and int(live.get("remaining_to_stable") or 0) == 0
    readiness_ok = ready.get("status") == "READY_WITH_AUTHORIZATION" and bool(ready.get("actual_canary_ready")) and bool(ready.get("skill_promotion_ready"))
    canary_operator_ok = bool(canary.get("enabled")) and canary.get("mode") == "operator" and bool(canary.get("operator_toggle_enabled"))
    hard_denies = set(canary.get("denied_intents") or []) | set(canary.get("hard_denied_intents") or [])
    hard_denies_ok = HARD_DENIED.issubset(hard_denies)
    switch_killed = bool(switch.get("kill_switch")) or switch.get("mode") == "killed" or switch.get("enabled") is False
    rollback_ready = bool((switch.get("watchdog") or {}).get("rollback_on_failure")) or bool(switch.get("watchdog_enabled"))

    answer_missing = []
    if not strict_100:
        answer_missing.append("strict_live_100_missing")
    if not readiness_ok:
        answer_missing.append("readiness_not_authorized")
    # Observe-only is allowed while switch is killed; replacement is not.
    shadow_pass = (canary_status.get("shadow_canary") or {}).get("status") == "PASS_SHADOW_ANSWER_CHAIN_CANARY"
    route_canary_pass = (canary_status.get("route_canary") or {}).get("status") == "PASS_LIMITED_ROUTE_ENFORCE_CANARY"
    limited_active = activation.get("status") == "PASS_LIMITED_SUPPORT_ACTIVATION"
    answer_status = "LIMITED_SUPPORT_REPLACED" if limited_active else ("SHADOW_CANARY_PASS" if shadow_pass else ("OBSERVE_ONLY_READY" if not answer_missing else "NOT_REPLACED"))

    route_missing = []
    if not strict_100:
        route_missing.append("strict_live_100_missing")
    if not readiness_ok:
        route_missing.append("readiness_not_authorized")
    if not canary_operator_ok:
        route_missing.append("operator_canary_not_ready")
    if not hard_denies_ok:
        route_missing.append("hard_denies_not_configured")
    if not rollback_ready:
        route_missing.append("rollback_not_ready")
    route_status = "LIMITED_SUPPORT_ENFORCED" if limited_active else ("LIMITED_SUPPORT_CANARY_PASS" if route_canary_pass else ("LIMITED_SUPPORT_ENFORCE_READY" if not route_missing else "ROUTE_ENFORCE_FALSE"))

    next_safe_action = "monitor_limited_support_lane" if limited_active else ("activate_limited_support_answer_chain_and_route_enforce" if shadow_pass and route_canary_pass else ("shadow_answer_chain_canary" if answer_status == "OBSERVE_ONLY_READY" else "fix_answer_chain_preconditions"))
    if route_status == "LIMITED_SUPPORT_ENFORCE_READY" and answer_status == "OBSERVE_ONLY_READY":
        next_safe_action = "run_shadow_answer_chain_canary_then_limited_route_enforce_canary"

    st = {
        "schema": "PGGAnswerChainRoutePreflight/v1",
        "ts": time.time(),
        "status": (
            "PREFLIGHT_LIMITED_SUPPORT_ACTIVE"
            if limited_active
            else (
                "PREFLIGHT_CANARIES_PASS_READY_FOR_LIMITED_ACTIVATION"
                if shadow_pass and route_canary_pass
                else ("PREFLIGHT_READY_FOR_SHADOW_CANARY" if answer_status == "OBSERVE_ONLY_READY" and route_status == "LIMITED_SUPPORT_ENFORCE_READY" else "PREFLIGHT_HOLD")
            )
        ),
        "answer_chain_status": answer_status,
        "route_enforce_status": route_status,
        "production_answer_chain_replaced": "limited_support_lane" if limited_active else False,
        "route_enforce_for_skillflow": "limited_support_lane" if limited_active else False,
        "strict_100": strict_100,
        "readiness_ok": readiness_ok,
        "canary_operator_ok": canary_operator_ok,
        "hard_denies_ok": hard_denies_ok,
        "production_switch_killed": switch_killed,
        "rollback_ready": rollback_ready,
        "allowed_scope": "exact/general bounded support lane only",
        "denied_scope": sorted(HARD_DENIED),
        "missing_requirements": {
            "answer_chain": answer_missing,
            "route_enforce": route_missing,
        },
        "next_safe_action": next_safe_action,
        "source_paths": {
            "live": str(LIVE),
            "readiness": str(READINESS),
            "production": str(PROD),
            "switch": str(SWITCH),
            "route_canary": str(ROUTE_CANARY),
        },
        "boundary": BOUNDARY,
    }
    st["summary_zh"] = (
        f"answer-chain/route preflight：{st['status']}；answer_chain={answer_status}；"
        f"route_enforce={route_status}；next={next_safe_action}；"
        f"production_answer_chain_replaced={st['production_answer_chain_replaced']}；"
        f"route_enforce_for_skillflow={st['route_enforce_for_skillflow']}。"
    )
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    ns = ap.parse_args(argv)
    out = evaluate()
    print(out["summary_zh"] if ns.summary else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
