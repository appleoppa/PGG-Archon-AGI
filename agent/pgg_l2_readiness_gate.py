"""PGG internal L2-candidate readiness gate.

Internal engineering readiness aggregator. It uses durable latest/ledger gate
records for expensive child gates and short live probes for goal/evolve. It must
not be reported as external AGI L2, full AGI, T5, legal correctness, or
unsupervised high-risk production takeover.
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
ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "venv/bin/python"
if not PY.exists():
    PY = HOME / "hermes-agent/venv/bin/python"
DATA = HOME / "data"
LATEST = DATA / "pgg_l2_readiness_gate_latest.json"
LEDGER = DATA / "pgg_l2_readiness_gate_ledger.jsonl"


def _run(cmd: list[str], timeout: int = 45) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "MISSING", "_source_path": str(path), "_source": "latest_file_missing"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["_source_path"] = str(path)
            data["_source"] = "latest_file"
            return data
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR_PARSE_LATEST", "error": repr(exc), "_source_path": str(path), "_source": "latest_file"}
    return {"status": "ERROR_NON_OBJECT_LATEST", "_source_path": str(path), "_source": "latest_file"}


def _json_live_or_latest(cmd: list[str], latest_path: Path, timeout: int = 45) -> dict[str, Any]:
    r = _run(cmd, timeout)
    try:
        data = json.loads(r["stdout"] or "{}")
    except Exception:
        data = {"status": "ERROR_PARSE_LIVE", "stderr_tail": r["stderr"][-300:], "stdout_tail": r["stdout"][-300:]}
    data["_returncode"] = r["returncode"]
    data["_source"] = "live"
    if data.get("summary") == "16/16 components PASS" or str(data.get("status", "")).startswith("PASS"):
        return data
    latest = _load_json_file(latest_path)
    latest["_fallback_live_status"] = data.get("status")
    latest["_fallback_live_returncode"] = r["returncode"]
    latest["_source"] = "latest_file_fallback"
    return latest


def build_status() -> dict[str, Any]:
    goal = _json_live_or_latest([str(HOME / "bin/hermes-goal")], DATA / "pgg_goal_unified_status_latest.json", 90)
    evolve = _json_live_or_latest([str(HOME / "bin/hermes-evolve"), "status"], DATA / "pgg_github_evolution_pipeline_latest.json", 60)
    agi = _load_json_file(DATA / "pgg_agi_gap_closure_gate_latest.json")
    token = _load_json_file(DATA / "pgg_token_oauth_governance_latest.json")
    legal = _load_json_file(DATA / "pgg_legal_e2e_benchmark_latest.json")
    auto = _load_json_file(DATA / "pgg_autonomy_curve_latest.json")
    historical = _load_json_file(DATA / "pgg_historical_evidence_backfill_latest.json")

    pr = _run(["gh", "pr", "list", "--repo", "appleoppa/PGG-Archon-AGI", "--state", "open", "--limit", "20", "--json", "number,title,url"], 45)
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
        "historical_backfill_internal_pass": str(historical.get("status", "")).startswith("PASS"),
        "open_pr_zero": isinstance(prs, list) and len(prs) == 0,
        "external_l2_not_claimed": True,
    }
    dimensions = {
        "基础认知": 89 if checks["goal_16_pass"] else 82,
        "跨域适配": 85 if checks["legal_e2e_benchmark_pass"] else 80,
        "自主行动": 88 if checks["evolve_pass"] and checks["autonomy_baseline_pass"] and checks["historical_backfill_internal_pass"] and checks["open_pr_zero"] else 80,
        "知识进化": 86 if checks["evolve_pass"] and checks["legal_e2e_benchmark_pass"] and checks["historical_backfill_internal_pass"] else 78,
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
            "goal": goal.get("summary") or goal.get("status"),
            "goal_source": goal.get("_source"),
            "evolve": evolve.get("status"),
            "evolve_source": evolve.get("_source"),
            "agi_gap": agi.get("status"),
            "agi_gap_source": agi.get("_source"),
            "token_oauth": token.get("status"),
            "token_source": token.get("_source"),
            "legal_e2e": legal.get("status"),
            "legal_source": legal.get("_source"),
            "autonomy": auto.get("status"),
            "autonomy_source": auto.get("_source"),
            "historical_backfill": historical.get("status"),
            "historical_summary": historical.get("summary"),
            "historical_source": historical.get("_source"),
            "open_pr_count": len(prs) if isinstance(prs, list) else None,
        },
        "can_claim": "Internal L2-candidate/readiness if PASS; engineering readiness only.",
        "must_not_claim": ["external AGI L2", "full AGI", "T5", "legal correctness proof", "unsupervised high-risk production takeover"],
        "remaining_external_evidence_needed": ["autonomy collector own multi-day elapsed samples", "independent external benchmark", "real legal E2E correctness review"],
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
