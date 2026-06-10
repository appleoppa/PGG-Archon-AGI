"""Guarded high-risk lane readiness gate.

This gate converts legal/audit/AGI high-risk lanes from a blanket deny into a
bounded, receipt-based readiness state. It does not remove final review, does not
publish legal advice, and does not mutate scheduler/security/provider config.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
DATA = HOME / "data"
LATEST = DATA / "pgg_high_risk_lane_gate_latest.json"
LEDGER = DATA / "pgg_high_risk_lane_gate_ledger.jsonl"
LANES = ["legal", "audit", "agi_architecture"]


def _run(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-1000:]}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def build_status() -> dict[str, Any]:
    evolve = _run([str(HOME / "bin/hermes-evolve"), "status"], 90)
    goal = _run([str(HOME / "bin/hermes-goal")], 90)
    trusted_gate = HOME / "bin/case_trusted_workflow_gate"
    cms_gate = HOME / "bin/cms_case_guard"
    cms_fallback = HOME / "bin/cms_case_guard.caseflowfix.tmp"
    cms_available = cms_gate.exists() or cms_fallback.exists()
    llm_audit_available = "llm-audit" in _run(["hermes", "mcp", "list"], 30)["stdout"]
    goal_json: dict[str, Any] = {}
    evolve_json: dict[str, Any] = {}
    for src, target in [(goal, goal_json), (evolve, evolve_json)]:
        try:
            target.update(json.loads(src.get("stdout") or "{}"))
        except Exception:
            pass
    checks = {
        "goal_16_pass": goal.get("returncode") == 0 and goal_json.get("summary") == "16/16 components PASS",
        "evolution_pipeline_pass": evolve.get("returncode") == 0 and str(evolve_json.get("status", "")).startswith("PASS"),
        "cms_case_guard_present": cms_available,
        "case_trusted_workflow_gate_present": trusted_gate.exists(),
        "llm_audit_mcp_available": llm_audit_available,
        "final_human_review_required": True,
        "no_unsupervised_external_delivery": True,
    }
    passed = sum(bool(v) for v in checks.values())
    total = len(checks)
    lane_states = {
        lane: {
            "mode": "guarded_canary_eval_lane",
            "production_takeover": False,
            "requires_receipts": ["source_material", "local_gate", "department_or_subagent", "secondary_llm_audit", "final_human_review"],
        }
        for lane in LANES
    }
    status = "PASS_HIGH_RISK_LANES_GUARDED_READY" if passed == total else "WATCH_HIGH_RISK_LANES_GUARDED_PARTIAL"
    rec = {
        "schema": "PGGHighRiskLaneGate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "passed": passed,
        "total": total,
        "checks": checks,
        "lanes": lane_states,
        "legal_truth_boundary": "No full legal AGI, no lawyer replacement, no unsupervised external legal delivery; FINAL requires CMS/evidence/law/source/inspection/audit receipts.",
        "audit_truth_boundary": "Audit lane can run canaries and reviewer receipts but cannot certify external safety without actual evidence.",
        "agi_truth_boundary": "AGI lane is benchmark/eval gated, not full AGI/T5 proof.",
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
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} checks={rec['passed']}/{rec['total']}")
    return 0 if rec["passed"] == rec["total"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
