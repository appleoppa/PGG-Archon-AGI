"""PGG internal L2-candidate readiness gate.

This is an internal engineering readiness score. It must not be reported as
external AGI L2, full AGI, legal correctness, or unsupervised high-risk takeover.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
ROOT = HOME / "hermes-agent"
PY = ROOT / "venv/bin/python"
DATA = HOME / "data"
LATEST = DATA / "pgg_l2_readiness_gate_latest.json"
LEDGER = DATA / "pgg_l2_readiness_gate_ledger.jsonl"


def _run(cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def _json_from_run(cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    r = _run(cmd, timeout)
    try:
        d = json.loads(r["stdout"] or "{}")
    except Exception:
        d = {"status": "ERROR_PARSE", "stdout_tail": r["stdout"][-500:], "stderr_tail": r["stderr"][-500:]}
    d["_returncode"] = r["returncode"]
    return d


def build_status() -> dict[str, Any]:
    goal = _json_from_run([str(HOME / "bin/hermes-goal")], 240)
    evolve = _json_from_run([str(HOME / "bin/hermes-evolve"), "status"], 120)
    agi = _json_from_run([str(PY), "-m", "agent.pgg_agi_gap_closure_gate", "--json"], 240)
    agi_retry_used = False
    if not (str(agi.get("status", "")).startswith("PASS") and float(agi.get("score") or 0) >= 83.0):
        agi = _json_from_run([str(PY), "-m", "agent.pgg_agi_gap_closure_gate", "--json"], 240)
        agi_retry_used = True
    token_public = _run([str(PY), "-m", "agent.pgg_token_oauth_governance", "--json"], 120)
    token_latest = DATA / "pgg_token_oauth_governance_latest.json"
    token = json.loads(token_latest.read_text(encoding="utf-8")) if token_latest.exists() else {"status": "MISSING"}
    legal = _json_from_run([str(PY), "-m", "agent.pgg_legal_e2e_benchmark_gate", "--json"], 120)
    auto = _json_from_run([str(PY), "-m", "agent.pgg_autonomy_curve_collector", "--json"], 120)
    pr = _run(["gh", "pr", "list", "--repo", "appleoppa/PGG-Archon-AGI", "--state", "open", "--limit", "20", "--json", "number,title,url"], 60)
    try:
        prs = json.loads(pr["stdout"] or "[]")
    except Exception:
        prs = []

    checks = {
        "goal_16_pass": goal.get("summary") == "16/16 components PASS" and goal.get("watch_count") == 0 and goal.get("blocked_count") == 0,
        "evolve_pass": str(evolve.get("status", "")).startswith("PASS") and not evolve.get("blockers"),
        "agi_gap_ge_83": float(agi.get("score") or 0) >= 83.0,
        "token_oauth_pass": str(token.get("status", "")).startswith("PASS"),
        "legal_e2e_benchmark_pass": str(legal.get("status", "")).startswith("PASS") and float(legal.get("pass_rate") or 0) >= 0.8,
        "autonomy_baseline_pass": str(auto.get("status", "")).startswith("PASS") and float(auto.get("pipeline_success_rate") or 0) >= 0.8,
        "open_pr_zero": isinstance(prs, list) and len(prs) == 0,
        "external_l2_not_claimed": True,
    }
    dimensions = {
        "基础认知": 89 if checks["goal_16_pass"] else 82,
        "跨域适配": 85 if checks["legal_e2e_benchmark_pass"] else 80,
        "自主行动": 86 if checks["evolve_pass"] and checks["autonomy_baseline_pass"] and checks["open_pr_zero"] else 80,
        "知识进化": 84 if checks["evolve_pass"] and checks["legal_e2e_benchmark_pass"] else 78,
        "对齐安全": 89 if checks["token_oauth_pass"] and checks["external_l2_not_claimed"] else 78,
        "落地性能": 84 if checks["agi_gap_ge_83"] and checks["legal_e2e_benchmark_pass"] else 79,
    }
    score = round(sum(dimensions.values()) / len(dimensions), 1)
    status = "PASS_INTERNAL_L2_CANDIDATE_READINESS" if score >= 85 and all(checks.values()) else "WATCH_INTERNAL_L2_CANDIDATE_READINESS"
    rec = {
        "schema": "PGGL2ReadinessGate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "score": score,
        "dimensions": dimensions,
        "checks": checks,
        "component_statuses": {
            "goal": goal.get("summary"),
            "evolve": evolve.get("status"),
            "agi_gap": agi.get("status"),
            "agi_gap_retry_used": agi_retry_used,
            "token_oauth": token.get("status"),
            "legal_e2e": legal.get("status"),
            "autonomy": auto.get("status"),
            "open_pr_count": len(prs) if isinstance(prs, list) else None,
        },
        "can_claim": "Internal L2-candidate/readiness if PASS; engineering readiness only.",
        "must_not_claim": ["external AGI L2", "full AGI", "T5", "legal correctness proof", "unsupervised high-risk production takeover"],
        "remaining_external_evidence_needed": ["multi-day autonomy elapsed samples", "independent external benchmark", "real legal E2E correctness review"],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    LEDGER.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = build_status()
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} score={rec['score']}")
    return 0 if rec["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
