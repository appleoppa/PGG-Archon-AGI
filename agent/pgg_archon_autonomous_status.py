"""PGG Archon autonomous evolution read-only status dashboard.

Boundary: aggregates existing ledgers, manifest, cron, launchd and GeneDB state.
It performs no mutations and makes no AGI-completion claims.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class AutonomousEvolutionStatus:
    schema: str
    manifest_last_updated: str | None
    autonomous_loop: dict[str, Any]
    latest_loop_cycle: dict[str, Any]
    genedb_gene_347: dict[str, Any]
    cron_job: dict[str, Any]
    rust_watcher: dict[str, Any]
    latest_readiness_package: dict[str, Any]
    known_gaps: list[str]
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


def _cron_job(jobs_path: Path, job_id: str) -> dict[str, Any]:
    data = _load_json(jobs_path, {})
    jobs = data if isinstance(data, list) else data.get("jobs", []) if isinstance(data, dict) else []
    for job in jobs:
        if isinstance(job, dict) and (job.get("id") == job_id or job.get("job_id") == job_id):
            return {k: job.get(k) for k in ["id", "job_id", "name", "enabled", "schedule", "last_status", "next_run_at", "no_agent", "script"]}
    return {"status": "missing", "job_id": job_id}


def _gene_state(db_path: Path, gene_id: int) -> dict[str, Any]:
    if not db_path.expanduser().exists():
        return {"status": "missing_db", "db": str(db_path)}
    con = sqlite3.connect(db_path.expanduser())
    cur = con.cursor()
    try:
        gene = cur.execute("select id,name,pattern_type,quality_score,extracted_at from genes where id=?", (gene_id,)).fetchone()
        life = cur.execute(
            "select gene_id,state,quality_score,candidate_at,promoted_at from gene_lifecycle where gene_id=?", (gene_id,)
        ).fetchone()
        chain = cur.execute(
            "select id,gene_id,from_state,to_state,transitioned_at,trigger_phase from promotion_chain where gene_id=? order by id desc limit 1",
            (gene_id,),
        ).fetchone()
    finally:
        con.close()
    return {"gene": list(gene) if gene else None, "lifecycle": list(life) if life else None, "latest_promotion_chain": list(chain) if chain else None}


def _rust_watcher_status() -> dict[str, Any]:
    try:
        proc = subprocess.run(["launchctl", "print", "gui/501/ai.hermes.evol-watcher"], text=True, capture_output=True, timeout=10)
        out = proc.stdout + proc.stderr
        return {
            "exit": proc.returncode,
            "active": proc.returncode == 0 and "state = running" in out,
            "pid_present": "pid =" in out,
            "label": "ai.hermes.evol-watcher",
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc), "label": "ai.hermes.evol-watcher"}


def _latest_readiness(base: Path) -> dict[str, Any]:
    files = sorted(base.expanduser().glob("**/promotion_readiness_package.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {"status": "missing"}
    payload = _load_json(files[0], {})
    return {"path": str(files[0]), "status": payload.get("status"), "blockers": payload.get("blockers"), "generated_at": payload.get("generated_at")}


def build_status(*, home: str | Path | None = None) -> AutonomousEvolutionStatus:
    h = Path(home).expanduser() if home else Path.home()
    manifest = _load_json(h / ".hermes/data/EVOLUTION_MANIFEST.json", {})
    caps = manifest.get("capabilities", {}) if isinstance(manifest, dict) else {}
    loop_cap = caps.get("autonomous_evolution_loop", {}) if isinstance(caps, dict) else {}
    latest_cycle = _latest_jsonl(h / ".hermes/data/pgg-background-evolution/autonomous_loop_cycles.jsonl")
    gene = _gene_state(h / ".hermes/data/pgg_archon.db", 347)
    cron = _cron_job(h / ".hermes/cron/jobs.json", str(loop_cap.get("cron_job_id") or "c0fad245e325"))
    readiness = _latest_readiness(h / ".hermes/workspace/evolution/autonomous_loop")
    known_gaps = []
    if readiness.get("status") != "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW":
        known_gaps.append("latest promotion readiness package is not READY")
    if cron.get("enabled") is not True:
        known_gaps.append("autonomous evolution cron is not enabled")
    if not _rust_watcher_status().get("active"):
        known_gaps.append("Rust fused watcher is not confirmed active")
    if ((gene.get("lifecycle") or [None, None])[1]) != "promoted":
        known_gaps.append("gene_id=347 is not promoted")
    if "Claude" not in json.dumps(manifest, ensure_ascii=False) and True:
        known_gaps.append("Claude provider health remains externally unresolved unless separately verified")
    return AutonomousEvolutionStatus(
        schema="PGGAutonomousEvolutionStatus/v1",
        manifest_last_updated=manifest.get("last_updated") if isinstance(manifest, dict) else None,
        autonomous_loop=loop_cap,
        latest_loop_cycle={
            "status": latest_cycle.get("status"),
            "started_at": latest_cycle.get("started_at"),
            "finished_at": latest_cycle.get("finished_at"),
            "generated_count": latest_cycle.get("generated_count"),
            "error_count": latest_cycle.get("error_count"),
            "boundary": latest_cycle.get("boundary"),
        },
        genedb_gene_347=gene,
        cron_job=cron,
        rust_watcher=_rust_watcher_status(),
        latest_readiness_package=readiness,
        known_gaps=known_gaps,
        boundary="Read-only status dashboard; no mutations, no full AGI proof.",
    )


def write_status(*, output_path: str | Path, home: str | Path | None = None) -> dict[str, Any]:
    status = build_status(home=home)
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status_path": str(out), "known_gaps": status.known_gaps, "latest_loop_status": status.latest_loop_cycle.get("status")}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print/read PGG autonomous evolution status.")
    parser.add_argument("--output")
    args = parser.parse_args(list(argv) if argv is not None else None)
    status = build_status()
    payload = status.to_json_dict()
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
