"""PGG one-click full audit anti-regression gate.

Read-only gate for the user's natural-language trigger "一键全量审计".
It composes the already bounded gates and refuses historical/file-only success.
No provider/config/scheduler/security mutation is performed here.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "venv/bin/python"
if not PY.exists():
    PY = Path(sys.executable)
HOME = Path.home()
HERMES_BIN = HOME / ".hermes/bin"


def _run(cmd: list[str], timeout: int = 120, cwd: Path | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PATH"] = f"{HERMES_BIN}:{env.get('PATH','')}"
    try:
        cp = subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, capture_output=True, text=True, timeout=timeout)
        return {"cmd": cmd, "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
    except Exception as e:
        return {"cmd": cmd, "returncode": -1, "stdout": "", "stderr": f"{type(e).__name__}: {e}"}


def _json_from_stdout(rec: dict[str, Any]) -> dict[str, Any]:
    out = (rec.get("stdout") or "").strip()
    try:
        return json.loads(out)
    except Exception:
        return {}


def _add(checks: list[dict[str, Any]], name: str, ok: bool, info: Any = None) -> None:
    checks.append({"name": name, "ok": bool(ok), "info": info})


def build_status(run_provider_canary: bool = False, provider: str = "deepseek") -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}

    goal = _run([str(HERMES_BIN / "hermes-goal")], 180)
    goal_json = _json_from_stdout(goal)
    evidence["hermes_goal"] = {"returncode": goal["returncode"], "json": goal_json}
    _add(checks, "hermes_goal_16_of_16_pass", goal["returncode"] == 0 and goal_json.get("overall_status") == "PASS" and goal_json.get("summary") == "16/16 components PASS" and goal_json.get("watch_count") == 0 and goal_json.get("blocked_count") == 0, {"status": goal_json.get("overall_status"), "summary": goal_json.get("summary"), "watch": goal_json.get("watch_count"), "blocked": goal_json.get("blocked_count")})

    omni = _run([str(HERMES_BIN / "omniroute_ui_status"), "--json"], 60)
    omni_json = _json_from_stdout(omni)
    evidence["omniroute_ui_status"] = {"returncode": omni["returncode"], "json": omni_json}
    _add(checks, "omniroute_ui_15_of_15_pass", omni["returncode"] == 0 and omni_json.get("status") == "PASS_OMNIROUTE_UI_PRACTICAL_READY_CONFIG_SYNC" and omni_json.get("passed") == omni_json.get("total") == 15, {"status": omni_json.get("status"), "passed": omni_json.get("passed"), "total": omni_json.get("total")})

    probe = _run([str(HERMES_BIN / "pgg_omniroute_provider_probe_gate"), "--json"], 60)
    probe_json = _json_from_stdout(probe)
    evidence["provider_probe_gate"] = {"returncode": probe["returncode"], "json": probe_json}
    _add(checks, "provider_probe_31_of_31_pass", probe["returncode"] == 0 and probe_json.get("status") == "PASS_OMNIROUTE_PROVIDER_PROBE_GATE_V109" and probe_json.get("passed") == probe_json.get("total") == 31, {"status": probe_json.get("status"), "passed": probe_json.get("passed"), "total": probe_json.get("total")})

    guarded_cmd = [str(PY), "-m", "agent.pgg_guarded_production_enable_gate", "--json"]
    if run_provider_canary:
        guarded_cmd += ["--provider-canary", "--provider", provider]
    guarded = _run(guarded_cmd, 180)
    guarded_json = _json_from_stdout(guarded)
    evidence["guarded_production_gate"] = {"returncode": guarded["returncode"], "json": guarded_json}
    expected_total = 11 if run_provider_canary else 10
    _add(checks, f"guarded_gate_{expected_total}_of_{expected_total}_pass", guarded["returncode"] == 0 and guarded_json.get("status") == "PASS_GUARDED_STRICT_EXACT_GENERAL_PRODUCTION_ACTIVE" and guarded_json.get("passed") == guarded_json.get("total") == expected_total, {"status": guarded_json.get("status"), "passed": guarded_json.get("passed"), "total": guarded_json.get("total")})

    try:
        from agent.memory_system_status import build_memory_system_status
        memory_json = build_memory_system_status()
        overall = memory_json.get("overall") or {}
        memory_rc = 0
    except Exception as exc:  # pragma: no cover - defensive gate surface
        memory_json = {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
        overall = {}
        memory_rc = 1
    evidence["memory_system"] = {"returncode": memory_rc, "json": memory_json}
    _add(checks, "memory_system_100_no_failed_watch", memory_rc == 0 and overall.get("score_percent") == 100.0 and overall.get("failed_or_watch") == [], {"score": overall.get("score_percent"), "failed_or_watch": overall.get("failed_or_watch")})

    neuron = _run([str(HOME / ".local/bin/神经元系统"), "--json"], 120)
    neuron_json = _json_from_stdout(neuron)
    evidence["neuron_system"] = {"returncode": neuron["returncode"], "json": neuron_json if neuron_json else {"stdout_head": neuron.get("stdout", "")[:500]}}
    # This gate requires the status surface to be readable/pass, but preserves candidate-only HOLD boundaries.
    nstatus = str(neuron_json.get("status") or neuron.get("stdout", ""))
    _add(checks, "neuron_system_pass_or_readable_with_hold_boundary", neuron["returncode"] == 0 and ("PASS" in nstatus or "状态: PASS" in neuron.get("stdout", "")), nstatus[:180])

    tests = _run([str(PY), "-m", "pytest", "-q", "tests/agent/test_pgg_goal_unified_status.py", "tests/agent/test_department_memory_runtime.py"], 180)
    evidence["focused_tests"] = {"returncode": tests["returncode"], "stdout": tests["stdout"], "stderr": tests["stderr"]}
    _add(checks, "focused_tests_pass", tests["returncode"] == 0 and "6 passed" in tests.get("stdout", ""), (tests.get("stdout", "") + tests.get("stderr", ""))[-500:])

    docker = _run(["docker", "info", "--format", "{{.ServerVersion}}"], 30)
    evidence["docker"] = {"returncode": docker["returncode"], "stdout": docker["stdout"], "stderr": docker["stderr"]}
    _add(checks, "docker_runtime_ready_for_apexagi_vt", docker["returncode"] == 0 and bool(docker.get("stdout", "").strip()), (docker.get("stdout") or docker.get("stderr") or "")[:120])

    passed = sum(1 for c in checks if c["ok"])
    total = len(checks)
    status = "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION" if passed == total else "HOLD_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION"
    return {
        "schema": "PGGOneClickFullAuditAntiRegressionGate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "passed": passed,
        "total": total,
        "checks": checks,
        "evidence": evidence,
        "provider_canary": run_provider_canary,
        "boundary": "Read-only anti-regression gate; no OAuth/provider/config/scheduler/security mutation; not full AGI/T5/external benchmark/legal correctness proof.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--provider-canary", action="store_true")
    ap.add_argument("--provider", default="deepseek")
    args = ap.parse_args(argv)
    rec = build_status(run_provider_canary=args.provider_canary, provider=args.provider)
    ledger = HOME / ".hermes/data/pgg_one_click_full_audit_gate_ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    else:
        print(rec["status"])
        print(f"checks={rec['passed']}/{rec['total']}")
        print(f"ledger={ledger}")
        for c in rec["checks"]:
            print("PASS" if c["ok"] else "FAIL", c["name"], c.get("info"))
    return 0 if rec["passed"] == rec["total"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
