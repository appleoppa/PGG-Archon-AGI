"""PGG unfinished-items truth gate.

Separates current active blockers from historical/stale WATCH latest files.
Boundary: read-only status classification only; no deletion, no mutation of
providers/scheduler/security/credentials/production routes.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv/bin/python"
if not PY.exists():
    PY = ROOT / "venv/bin/python"
if not PY.exists():
    PY = HOME / "hermes-agent/.venv/bin/python"
if not PY.exists():
    PY = HOME / "hermes-agent/venv/bin/python"
DATA = HOME / "data"
LATEST = DATA / "pgg_unfinished_items_gate_latest.json"
LEDGER = DATA / "pgg_unfinished_items_gate_ledger.jsonl"

HISTORICAL_WATCH_FILES = {
    "goal_mcp_cli_github_self_evolution_latest.json": "readonly baseline with broad GitHub scope; historical governance surface",
    "pgg_evm_e2e_trend_latest.json": "trend observe surface; requires longitudinal samples/time",
    "pgg_unified_formula_score_latest.json": "bounded formula score surface; not a live pass/fail gate",
}


def _run(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def _json(cmd: list[str], timeout: int = 90) -> Any:
    r = _run(cmd, timeout)
    try:
        data = json.loads(r["stdout"] or "{}")
    except Exception:
        data = {"status": "ERROR_PARSE", "stdout_tail": r["stdout"][-300:], "stderr_tail": r["stderr"][-300:]}
    if isinstance(data, dict):
        data["_returncode"] = r["returncode"]
    return data


def _status_of_latest(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("status") or data.get("overall_status") or data.get("summary") or "")
    except Exception as exc:  # noqa: BLE001
        return f"ERROR_PARSE:{type(exc).__name__}"


def build_status() -> dict[str, Any]:
    git = _run(["git", "status", "--porcelain=v1"], 30)
    dirty_lines = [line for line in git.get("stdout", "").splitlines() if line.strip()]
    prs = _json(["gh", "pr", "list", "--repo", "appleoppa/PGG-Archon-AGI", "--state", "open", "--limit", "50", "--json", "number,title,headRefName,url"], 60)
    if not isinstance(prs, list):
        prs = []

    goal = _json([str(HOME / "bin/hermes-goal")], 120)
    one = _json([str(PY), "-m", "agent.pgg_one_click_full_audit_gate", "--json"], 240)
    l2 = _json([str(PY), "-m", "agent.pgg_l2_readiness_gate", "--json"], 240)

    active: list[dict[str, Any]] = []
    if dirty_lines:
        active.append({"kind": "git_dirty", "items": dirty_lines})
    if prs:
        active.append({"kind": "open_prs", "items": prs})
    if goal.get("summary") != "16/16 components PASS" or goal.get("watch_count") or goal.get("blocked_count"):
        active.append({"kind": "goal", "status": goal.get("overall_status"), "summary": goal.get("summary"), "watch": goal.get("watch_count"), "blocked": goal.get("blocked_count")})
    if one.get("status") != "PASS_ONE_CLICK_FULL_AUDIT_ANTI_REGRESSION":
        active.append({"kind": "one_click", "status": one.get("status"), "passed": one.get("passed"), "total": one.get("total")})
    if l2.get("status") != "PASS_INTERNAL_L2_CANDIDATE_READINESS":
        active.append({"kind": "l2_readiness", "status": l2.get("status"), "score": l2.get("score")})

    stale: list[dict[str, Any]] = []
    for name, reason in HISTORICAL_WATCH_FILES.items():
        path = DATA / name
        if path.exists():
            st = _status_of_latest(path)
            if any(token in st for token in ("WATCH", "HOLD", "BLOCK", "FAIL", "ERROR")):
                stale.append({"file": str(path), "status": st, "reason": reason})

    status = "PASS_NO_ACTIVE_UNFINISHED_ITEMS" if not active else "WATCH_ACTIVE_UNFINISHED_ITEMS"
    rec = {
        "schema": "PGGUnfinishedItemsGate/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "active_unfinished_count": len(active),
        "active_unfinished": active,
        "stale_historical_watch_count": len(stale),
        "stale_historical_watch": stale,
        "core_readback": {
            "goal": {"summary": goal.get("summary"), "watch": goal.get("watch_count"), "blocked": goal.get("blocked_count")},
            "one_click": {"status": one.get("status"), "passed": one.get("passed"), "total": one.get("total")},
            "l2": {"status": l2.get("status"), "score": l2.get("score")},
            "open_pr_count": len(prs),
        },
        "remaining_external_evidence_needed": [
            "autonomy collector own multi-day elapsed samples",
            "external/community benchmark or evaluation evidence track (no single official AGI standard assumed)",
            "real legal E2E correctness review",
        ],
        "boundary": "Read-only classifier. Stale historical WATCH files are not current blockers; no deletion or mutation performed. Not external AGI L2/full AGI/T5/legal correctness proof.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(rec, ensure_ascii=False)
    tmp = LATEST.with_suffix(LATEST.suffix + ".tmp")
    tmp.write_text(encoded + "\n", encoding="utf-8")
    tmp.replace(LATEST)
    LEDGER.open("a", encoding="utf-8").write(encoded + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = build_status()
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} active={rec['active_unfinished_count']} stale={rec['stale_historical_watch_count']}")
    return 0 if rec["active_unfinished_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
