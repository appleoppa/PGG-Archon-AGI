"""PGG Archon cron event audit.

Boundary: read-only audit for the no-agent autonomous cron job, cycle ledger,
and append-only event ledger. It does not create/update cron jobs, replace
launchd, mutate GeneDB, or claim AGI completion.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


DEFAULT_JOB_ID = "c0fad245e325"


@dataclass(frozen=True)
class CronEventAuditResult:
    schema: str
    status: str
    cron_job_id: str
    checks: dict[str, bool]
    blockers: list[str]
    cron_job: dict[str, Any]
    latest_cycle: dict[str, Any]
    latest_event: dict[str, Any]
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.expanduser().read_text(encoding="utf-8"))
    except Exception:
        return default


def _latest_jsonl(path: Path) -> dict[str, Any]:
    try:
        lines = [line for line in path.expanduser().read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(lines[-1]) if lines else {}
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc), "path": str(path)}


def _find_cron_job(jobs_path: Path, job_id: str) -> dict[str, Any]:
    data = _load_json(jobs_path, {})
    jobs = data if isinstance(data, list) else data.get("jobs", []) if isinstance(data, dict) else []
    for job in jobs:
        if isinstance(job, dict) and (job.get("id") == job_id or job.get("job_id") == job_id):
            return job
    return {"status": "missing", "job_id": job_id}


def evaluate_cron_event_audit(*, home: str | Path | None = None, job_id: str = DEFAULT_JOB_ID) -> CronEventAuditResult:
    h = Path(home).expanduser() if home else Path.home()
    cron_job = _find_cron_job(h / ".hermes/cron/jobs.json", job_id)
    latest_cycle = _latest_jsonl(h / ".hermes/data/pgg-background-evolution/autonomous_loop_cycles.jsonl")
    latest_event = _latest_jsonl(h / ".hermes/data/pgg-background-evolution/autonomous_events.jsonl")
    checks = {
        "cron_job_present": cron_job.get("status") != "missing",
        "cron_enabled": cron_job.get("enabled") is True,
        "cron_last_status_ok": cron_job.get("last_status") in ("ok", "success", None),
        "cron_no_agent": cron_job.get("no_agent") is True,
        "cycle_ledger_readable": latest_cycle.get("schema") == "PGGAutonomousEvolutionLoopCycle/v1",
        "cycle_status_pass": latest_cycle.get("status") == "PASS",
        "event_ledger_readable": latest_event.get("schema") == "PGGAutonomousEvolutionEvent/v1",
        "event_source_python_loop": latest_event.get("source") == "python_autonomous_loop",
        "event_status_matches_cycle": latest_event.get("status") == latest_cycle.get("status"),
        "event_references_cycle_ledger": bool((latest_event.get("payload") or {}).get("cycle_ledger")),
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "PASS_CRON_EVENT_AUDIT" if not blockers else "WATCH_CRON_EVENT_AUDIT"
    return CronEventAuditResult(
        schema="PGGArchonCronEventAuditResult/v1",
        status=status,
        cron_job_id=job_id,
        checks=checks,
        blockers=blockers,
        cron_job={k: cron_job.get(k) for k in ["id", "job_id", "name", "enabled", "schedule", "last_status", "next_run_at", "no_agent", "script"]},
        latest_cycle={k: latest_cycle.get(k) for k in ["schema", "started_at", "finished_at", "status", "generated_count", "error_count", "event_ledger_status", "event_ledger_path"]},
        latest_event={k: latest_event.get(k) for k in ["schema", "event_id", "created_at", "source", "event_type", "status", "payload"]},
        boundary="Read-only cron/event audit; no cron mutation, no runtime replacement, no GeneDB mutation, no full AGI proof.",
    )


def write_cron_event_audit(*, output_dir: str | Path, home: str | Path | None = None, job_id: str = DEFAULT_JOB_ID) -> dict[str, Any]:
    result = evaluate_cron_event_audit(home=home, job_id=job_id)
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "cron_event_audit_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of autonomous cron job and event ledger.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--home")
    parser.add_argument("--job-id", default=DEFAULT_JOB_ID)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(write_cron_event_audit(output_dir=args.output_dir, home=args.home, job_id=args.job_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
