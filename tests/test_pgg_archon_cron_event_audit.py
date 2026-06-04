from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_cron_event_audit import evaluate_cron_event_audit, main


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _home(tmp_path: Path, *, event_status: str = "PASS", cycle_status: str = "PASS") -> Path:
    home = tmp_path
    _write(home / ".hermes/cron/jobs.json", {"jobs": [{
        "id": "c0fad245e325",
        "name": "PGG Archon autonomous queue-to-proposal evolution loop",
        "enabled": True,
        "last_status": "ok",
        "no_agent": True,
        "script": "pgg_autonomous_evolution_loop.py",
    }]})
    cycle = {
        "schema": "PGGAutonomousEvolutionLoopCycle/v1",
        "status": cycle_status,
        "started_at": "t1",
        "finished_at": "t2",
        "generated_count": 0,
        "error_count": 0,
        "event_ledger_status": "PASS",
        "event_ledger_path": str(home / ".hermes/data/pgg-background-evolution/autonomous_events.jsonl"),
    }
    event = {
        "schema": "PGGAutonomousEvolutionEvent/v1",
        "event_id": "abc",
        "created_at": "t2",
        "source": "python_autonomous_loop",
        "event_type": "cycle_completed",
        "status": event_status,
        "payload": {"cycle_ledger": str(home / ".hermes/data/pgg-background-evolution/autonomous_loop_cycles.jsonl")},
    }
    ledger_dir = home / ".hermes/data/pgg-background-evolution"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    (ledger_dir / "autonomous_loop_cycles.jsonl").write_text(json.dumps(cycle) + "\n", encoding="utf-8")
    (ledger_dir / "autonomous_events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    return home


def test_cron_event_audit_passes_when_cron_cycle_event_align(tmp_path: Path) -> None:
    result = evaluate_cron_event_audit(home=_home(tmp_path))
    assert result.status == "PASS_CRON_EVENT_AUDIT"
    assert result.blockers == []
    assert result.checks["event_status_matches_cycle"] is True


def test_cron_event_audit_blocks_status_mismatch(tmp_path: Path) -> None:
    result = evaluate_cron_event_audit(home=_home(tmp_path, event_status="WATCH", cycle_status="PASS"))
    assert result.status == "WATCH_CRON_EVENT_AUDIT"
    assert "event_status_matches_cycle" in result.blockers


def test_main_writes_cron_event_audit(tmp_path: Path, capsys) -> None:
    home = _home(tmp_path / "home")
    assert main(["--home", str(home), "--output-dir", str(tmp_path / "out")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS_CRON_EVENT_AUDIT"
    assert Path(printed["result"]).is_file()
