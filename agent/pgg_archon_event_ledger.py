"""PGG Archon autonomous evolution event ledger.

Boundary: append-only JSONL side-channel shared by Python autonomous loop and
Rust watcher observers. This module does not replace launchd, mutate GeneDB, or
claim AGI completion.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_LEDGER = Path.home() / ".hermes/data/pgg-background-evolution/autonomous_events.jsonl"


@dataclass(frozen=True)
class AutonomousEvolutionEvent:
    schema: str
    event_id: str
    created_at: str
    source: str
    event_type: str
    status: str
    payload: dict[str, Any]
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_event_id(source: str, event_type: str, created_at: str, payload: Mapping[str, Any]) -> str:
    import hashlib

    raw = json.dumps({"source": source, "event_type": event_type, "created_at": created_at, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def build_event(*, source: str, event_type: str, status: str, payload: Mapping[str, Any] | None = None) -> AutonomousEvolutionEvent:
    created_at = _now()
    clean_payload = dict(payload or {})
    return AutonomousEvolutionEvent(
        schema="PGGAutonomousEvolutionEvent/v1",
        event_id=_stable_event_id(source, event_type, created_at, clean_payload),
        created_at=created_at,
        source=source,
        event_type=event_type,
        status=status,
        payload=clean_payload,
        boundary="Append-only event ledger; no runtime replacement, no GeneDB mutation, no full AGI proof.",
    )


def append_event(event: AutonomousEvolutionEvent, *, ledger_path: str | Path = DEFAULT_LEDGER) -> dict[str, Any]:
    path = Path(ledger_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_json_dict(), ensure_ascii=False) + "\n")
    return {"ledger": str(path), "event_id": event.event_id, "status": event.status}


def load_events(*, ledger_path: str | Path = DEFAULT_LEDGER, limit: int | None = None) -> list[dict[str, Any]]:
    path = Path(ledger_path).expanduser()
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit is not None:
        lines = lines[-limit:]
    return [json.loads(line) for line in lines]


def summarize_events(*, ledger_path: str | Path = DEFAULT_LEDGER, limit: int = 50) -> dict[str, Any]:
    events = load_events(ledger_path=ledger_path, limit=limit)
    by_source: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for event in events:
        by_source[str(event.get("source"))] = by_source.get(str(event.get("source")), 0) + 1
        by_status[str(event.get("status"))] = by_status.get(str(event.get("status")), 0) + 1
    return {
        "schema": "PGGAutonomousEvolutionEventSummary/v1",
        "ledger": str(Path(ledger_path).expanduser()),
        "event_count": len(events),
        "latest_event": events[-1] if events else None,
        "by_source": by_source,
        "by_status": by_status,
        "boundary": "Read-only event summary; no mutation beyond optional append operations.",
    }


def observe_rust_watcher_event() -> AutonomousEvolutionEvent:
    try:
        proc = subprocess.run(["launchctl", "print", "gui/501/ai.hermes.evol-watcher"], text=True, capture_output=True, timeout=10)
        text = proc.stdout + proc.stderr
        active = proc.returncode == 0 and "state = running" in text
        pid_present = "pid =" in text
        status = "PASS" if active else "WATCH"
        payload = {"label": "ai.hermes.evol-watcher", "launchctl_exit": proc.returncode, "active": active, "pid_present": pid_present}
    except Exception as exc:  # noqa: BLE001
        status = "WATCH"
        payload = {"label": "ai.hermes.evol-watcher", "error": repr(exc)}
    return build_event(source="rust_fused_watcher_observer", event_type="watcher_status", status=status, payload=payload)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append/read PGG autonomous evolution events.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--source")
    parser.add_argument("--event-type")
    parser.add_argument("--status")
    parser.add_argument("--payload-json", default="{}")
    parser.add_argument("--observe-rust-watcher", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.summary:
        print(json.dumps(summarize_events(ledger_path=args.ledger, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.observe_rust_watcher:
        print(json.dumps(append_event(observe_rust_watcher_event(), ledger_path=args.ledger), ensure_ascii=False, indent=2))
        return 0
    if not (args.source and args.event_type and args.status):
        parser.error("--source, --event-type and --status are required unless --summary/--observe-rust-watcher is used")
    payload = json.loads(args.payload_json)
    if not isinstance(payload, dict):
        raise ValueError("--payload-json must decode to an object")
    event = build_event(source=args.source, event_type=args.event_type, status=args.status, payload=payload)
    print(json.dumps(append_event(event, ledger_path=args.ledger), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
