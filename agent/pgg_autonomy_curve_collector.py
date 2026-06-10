"""PGG autonomy curve collector.

Collects real bounded autonomy evidence over time. It does not claim long-term
unsupervised AGI from a single sample; it builds a ledger for success rate,
self-fix rate, cost/latency placeholders, rollback count, and PR backlog.
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
LEDGER = DATA / "pgg_autonomy_curve_ledger.jsonl"
LATEST = DATA / "pgg_autonomy_curve_latest.json"


def _run(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-1000:]}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def _tail_jsonl(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            pass
    return rows


def collect() -> dict[str, Any]:
    evolve_rows = _tail_jsonl(DATA / "pgg_github_evolution_pipeline_ledger.jsonl", 200)
    statuses = [str(r.get("status") or "") for r in evolve_rows]
    pass_count = sum(s.startswith("PASS") for s in statuses)
    watch_count = sum(s.startswith("WATCH") or s.startswith("HOLD") for s in statuses)
    fail_count = sum(s.startswith("FAIL") or s.startswith("ERROR") or s.startswith("BLOCK") for s in statuses)
    total = len(statuses)

    pr = _run(["gh", "pr", "list", "--repo", "appleoppa/PGG-Archon-AGI", "--state", "open", "--limit", "50", "--json", "number,title,headRefName,url"], timeout=45)
    open_prs: list[Any] = []
    if pr["returncode"] == 0:
        try:
            parsed = json.loads(pr["stdout"] or "[]")
            open_prs = parsed if isinstance(parsed, list) else []
        except Exception:
            open_prs = []

    cron = _run(["hermes", "cron", "list", "--all"], timeout=30)
    git = _run(["git", "-C", str(HOME / "hermes-agent"), "status", "--short", "--branch"], timeout=20)

    success_rate = round(pass_count / total, 4) if total else None
    readiness = 0
    checks = {
        "ledger_present": total > 0,
        "recent_pipeline_success_rate_ge_0_80": success_rate is not None and success_rate >= 0.80,
        "open_pr_backlog_le_2": len(open_prs) <= 2,
        "git_clean": git["returncode"] == 0 and "\n" not in git["stdout"].strip(),
        "cron_readable": cron["returncode"] == 0,
    }
    readiness = sum(bool(v) for v in checks.values())
    status = "PASS_AUTONOMY_CURVE_BASELINE_COLLECTING" if readiness >= 4 else "WATCH_AUTONOMY_CURVE_INSUFFICIENT"
    rec = {
        "schema": "PGGAutonomyCurveSample/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "pipeline_rows_sampled": total,
        "pipeline_pass_count": pass_count,
        "pipeline_watch_count": watch_count,
        "pipeline_fail_count": fail_count,
        "pipeline_success_rate": success_rate,
        "open_pr_count": len(open_prs),
        "open_prs": open_prs[:10],
        "cost_latency_available": False,
        "rollback_count_available": False,
        "multi_day_claim_allowed": False,
        "boundary": "Autonomy curve evidence collector; one sample starts a trend but does not prove multi-day unsupervised autonomy.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    LEDGER.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = collect()
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    else:
        print(rec["status"])
        print(f"success_rate={rec['pipeline_success_rate']} open_pr_count={rec['open_pr_count']} ledger={LEDGER}")
    return 0 if str(rec.get("status", "")).startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
