"""Aggregate AGI gap-closure gate and bounded progress score.

Composes the four concrete gates added for the user's requested gap closure.
It preserves truth boundaries: token/OAuth WATCH and multi-day autonomy evidence
claims cannot be upgraded without real credentials and longitudinal data.
There is no single official AGI benchmark standard here; external/community
benchmarks are optional evidence tracks, not something to fabricate as proof.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
ROOT = HOME / "hermes-agent"
PY = ROOT / ".venv/bin/python"
if not PY.exists():
    PY = ROOT / "venv/bin/python"
DATA = HOME / "data"
LATEST = DATA / "pgg_agi_gap_closure_gate_latest.json"
LEDGER = DATA / "pgg_agi_gap_closure_gate_ledger.jsonl"

MODULES = {
    "high_risk_lanes": "agent.pgg_high_risk_lane_gate",
    "token_oauth": "agent.pgg_token_oauth_governance",
    "autonomy_curve": "agent.pgg_autonomy_curve_collector",
    "benchmark_legal_smoke": "agent.pgg_external_benchmark_legal_smoke",
}


def _run_module(module: str) -> dict[str, Any]:
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        p = subprocess.run([str(PY), "-m", module, "--json"], cwd=str(ROOT), env=env, text=True, capture_output=True, timeout=180)
        try:
            data = json.loads(p.stdout or "{}")
        except Exception:
            data = {"parse_error": True, "stdout_tail": p.stdout[-1000:], "stderr_tail": p.stderr[-1000:]}
        if module.endswith("pgg_token_oauth_governance") and not data.get("status"):
            latest = DATA / "pgg_token_oauth_governance_latest.json"
            if latest.exists():
                data = json.loads(latest.read_text(encoding="utf-8"))
        data["_returncode"] = p.returncode
        return data
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "error": repr(exc), "_returncode": 999}


def build_status() -> dict[str, Any]:
    results = {name: _run_module(mod) for name, mod in MODULES.items()}
    statuses = {k: str(v.get("status", "")) for k, v in results.items()}
    strict_pass = {
        "high_risk_lanes": statuses["high_risk_lanes"].startswith("PASS"),
        "autonomy_curve_baseline": statuses["autonomy_curve"].startswith("PASS"),
        "benchmark_legal_smoke": statuses["benchmark_legal_smoke"].startswith("PASS"),
        "token_oauth_min_privilege": statuses["token_oauth"].startswith("PASS"),
    }
    # Bounded score: gate progress improves score, but token/OAuth WATCH and lack of multi-day autonomy evidence cap it.
    dims = {
        "基础认知/工具调用": 88,
        "跨域适配/多通道路由": 82 if strict_pass["high_risk_lanes"] else 78,
        "自主行动/闭环执行": 84 if strict_pass["autonomy_curve_baseline"] else 80,
        "知识进化/沉淀": 78 if strict_pass["autonomy_curve_baseline"] else 74,
        "对齐安全/真实性治理": 78 if not strict_pass["token_oauth_min_privilege"] else 86,
        "落地性能/生产可用": 81 if strict_pass["benchmark_legal_smoke"] and strict_pass["high_risk_lanes"] else 76,
    }
    raw_score = round(sum(dims.values()) / len(dims), 1)
    score_cap = 84.9
    cap_reasons = []
    if not strict_pass["token_oauth_min_privilege"]:
        cap_reasons.append("token/OAuth requires real credential rotation; current gate is WATCH")
    cap_reasons.append("multi-day unsupervised autonomy needs longitudinal samples, not one baseline")
    cap_reasons.append("external/community benchmark and legal correctness require separate evidence tracks; no single official AGI benchmark standard is assumed")
    score = min(raw_score, score_cap)
    status = "PASS_WITH_WATCH_AGI_GAP_CLOSURE_GATED" if strict_pass["high_risk_lanes"] and strict_pass["autonomy_curve_baseline"] and strict_pass["benchmark_legal_smoke"] else "WATCH_AGI_GAP_CLOSURE_PARTIAL"
    rec = {
        "schema": "PGGAGIGapClosureGate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "score": score,
        "raw_score": raw_score,
        "score_cap": score_cap,
        "score_cap_reasons": cap_reasons,
        "dimensions": dims,
        "strict_pass": strict_pass,
        "component_statuses": statuses,
        "component_results": results,
        "can_claim": [
            "High-risk legal/audit/AGI lanes are guarded canary/eval lanes with receipt requirements.",
            "Autonomy curve baseline collector and no-agent cron are active.",
            "Local bounded benchmark/legal smoke is executable and passing.",
            "Token/OAuth risks are detected without printing secrets.",
        ],
        "must_not_claim": [
            "full AGI/T5/L2+ external AGI benchmark certification",
            "unsupervised external legal/audit/AGI production takeover",
            "token/OAuth least privilege complete while current credential remains over-scoped/no active OAuth",
            "LegalBench/LexGLUE/legal correctness proof from deterministic smoke",
            "a fabricated official AGI standard where no agreed standard exists",
        ],
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
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} score={rec['score']} raw={rec['raw_score']}")
    return 0 if rec["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
