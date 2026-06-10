"""PGG guarded production enable gate.

Read-only regression gate for the authorized exact/general guarded production lane.
It does not mutate scheduler/security/provider config and does not print secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
LOCAL_LOOPBACK_DASHBOARD_TOKEN = "omniroute-dashboard-token"
TOKEN = (
    os.environ.get("HERMES_OMNIROUTE_DASHBOARD_TOKEN")
    or os.environ.get("OMNIROUTE_DASHBOARD_TOKEN")
    or os.environ.get("HERMES_DASHBOARD_SESSION_TOKEN")
    or LOCAL_LOOPBACK_DASHBOARD_TOKEN
)
API = os.environ.get("HERMES_OMNIROUTE_API", "http://127.0.0.1:9197")
EXPECTED = {
    "production_answer_chain_replaced": "guarded_strict_exact_general",
    "credential_integration": "ENABLED_WITH_EXISTING_AUTH_JSON_POOL",
    "oauth_integration": "WATCH_NO_ACTIVE_OAUTH_CREDENTIAL",
    "account_pool_integration": "ENABLED_WITH_EXISTING_AUTH_JSON_POOL",
    "scheduler_security_core_mutated": False,
}


def _is_loopback_api(api: str | None = None) -> bool:
    target = api or API
    return target.startswith("http://127.0.0.1:") or target.startswith("http://localhost:")


def _request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if TOKEN and (TOKEN != LOCAL_LOOPBACK_DASHBOARD_TOKEN or _is_loopback_api()):
        headers["X-Hermes-Session-Token"] = TOKEN
    return headers


def _http_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 20) -> tuple[bool, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, method=method, headers=_request_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _add(checks: list[dict[str, Any]], name: str, ok: bool, info: Any = None) -> None:
    checks.append({"name": name, "ok": bool(ok), "info": info})


def _provider_canary(provider: str = "deepseek", timeout: int = 120) -> dict[str, Any]:
    ok, data = _http_json("/api/omniroute/call", "POST", {"provider": provider, "requested_provider": provider, "prompt": "Return exactly: GUARDED_PRODUCTION_CANARY_OK", "timeout": min(timeout, 120)}, timeout=min(timeout + 20, 150))
    if not ok:
        return {"success": False, "error": data}
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return data if isinstance(data, dict) else {"success": False, "raw": str(data)[:300]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--provider-canary", action="store_true", help="Run bounded exact/general provider canary through OmniRoute call endpoint.")
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args(argv)

    checks: list[dict[str, Any]] = []
    ok, snap = _http_json("/api/omniroute/snapshot", timeout=20)
    _add(checks, "snapshot_api_ok", ok and isinstance(snap, dict), {"selected": snap.get("selected_provider") if isinstance(snap, dict) else snap})
    if isinstance(snap, dict):
        for k, expected in EXPECTED.items():
            _add(checks, f"runtime_{k}_matches", snap.get(k) == expected, snap.get(k))
        prs = snap.get("production_runtime_status") or {}
        _add(checks, "runtime_status_present", isinstance(prs, dict) and str(prs.get("status", "")).startswith("PASS_"), prs.get("status") if isinstance(prs, dict) else None)
        _add(checks, "allowed_scope_exact_general", prs.get("allowed_scope") == "exact/general guarded production lane" if isinstance(prs, dict) else False, prs.get("allowed_scope") if isinstance(prs, dict) else None)
        denied = set(prs.get("denied_scope") or []) if isinstance(prs, dict) else set()
        _add(checks, "denied_high_risk_scopes_present", {"chinese_legal", "audit_judge", "agi_architecture_coding", "scheduler_security_mutation"}.issubset(denied), sorted(denied))
        auth = prs.get("auth_summary_no_secrets") if isinstance(prs, dict) else {}
        _add(checks, "auth_summary_no_secrets_present", isinstance(auth, dict) and "credential_pool_entry_count" in auth and "oauth_active_count" in auth, auth if isinstance(auth, dict) else None)
    canary = None
    if args.provider_canary:
        canary = _provider_canary(args.provider, args.timeout)
        _add(checks, "provider_canary_participated", bool(canary.get("participated")) and int(canary.get("visible_chars") or 0) > 0, {"provider": args.provider, "http_status": canary.get("http_status"), "visible_chars": canary.get("visible_chars"), "method": canary.get("method")})

    passed=sum(1 for c in checks if c["ok"])
    total=len(checks)
    status="PASS_GUARDED_STRICT_EXACT_GENERAL_PRODUCTION_ACTIVE" if passed == total else "HOLD_GUARDED_STRICT_EXACT_GENERAL_PRODUCTION_GATE"
    rec={"schema":"PGGGuardedProductionEnableGate/v1","generated_at":datetime.now(timezone.utc).isoformat(),"status":status,"passed":passed,"total":total,"checks":checks,"provider_canary":canary,"strict_score":round(100*passed/total,2) if total else 0,"boundary":"exact/general guarded production lane only; OAuth remains WATCH until active credential exists; no scheduler/security mutation; not full AGI/T5/legal correctness proof."}
    data_dir = HOME / "data"
    ledger = data_dir / "pgg_guarded_production_enable_gate_ledger.jsonl"
    latest = data_dir / "pgg_guarded_production_enable_gate_latest.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(rec, ensure_ascii=False)
    ledger.open("a", encoding="utf-8").write(encoded + "\n")
    tmp = latest.with_suffix(latest.suffix + ".tmp")
    tmp.write_text(encoded + "\n", encoding="utf-8")
    tmp.replace(latest)
    if args.json:
        print(json.dumps(rec,ensure_ascii=False,indent=2))
    else:
        print(status)
        print(f"checks={passed}/{total}")
        print(f"strict_score={rec['strict_score']}")
        print(f"ledger={ledger}")
        for c in checks:
            print("PASS" if c["ok"] else "FAIL", c["name"], c.get("info"))
    return 0 if passed == total else 2

if __name__ == "__main__":
    raise SystemExit(main())
