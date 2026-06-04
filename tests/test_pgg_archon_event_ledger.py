from __future__ import annotations

import json
from pathlib import Path

from agent import pgg_archon_event_ledger as ledger_mod
from agent.pgg_archon_event_ledger import append_event, build_event, load_events, main, observe_rust_watcher_event, summarize_events


def test_append_load_and_summarize_events(tmp_path: Path) -> None:
    ledger = tmp_path / "events.jsonl"
    event = build_event(source="python_loop", event_type="cycle", status="PASS", payload={"generated_count": 1})
    result = append_event(event, ledger_path=ledger)
    assert result["event_id"] == event.event_id
    events = load_events(ledger_path=ledger)
    assert len(events) == 1
    assert events[0]["payload"]["generated_count"] == 1
    summary = summarize_events(ledger_path=ledger)
    assert summary["event_count"] == 1
    assert summary["by_source"]["python_loop"] == 1
    assert summary["by_status"]["PASS"] == 1


def test_main_appends_and_summarizes(tmp_path: Path, capsys) -> None:
    ledger = tmp_path / "events.jsonl"
    assert main([
        "--ledger", str(ledger),
        "--source", "unit",
        "--event-type", "smoke",
        "--status", "PASS",
        "--payload-json", '{"x":1}',
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS"
    assert main(["--ledger", str(ledger), "--summary"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["event_count"] == 1


def test_observe_rust_watcher_event_mocked(monkeypatch) -> None:
    class Proc:
        returncode = 0
        stdout = "state = running\npid = 123\n"
        stderr = ""

    monkeypatch.setattr(ledger_mod.subprocess, "run", lambda *args, **kwargs: Proc())
    event = observe_rust_watcher_event()
    assert event.status == "PASS"
    assert event.payload["active"] is True
    assert event.payload["pid_present"] is True
