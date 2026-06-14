#!/usr/bin/env python3
"""Read-only observability ledger for PGGAgentLoopEvent/v1.

Writes compact, secret-safe event metadata for Exec Dashboard aggregation.
No provider/config/scheduler/security mutation. Fail-open by design.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

_ALLOWED_TYPES = {"tool_request", "tool_result", "compact_boundary", "loop_result", "stream_event"}
_LEDGER_NAME = "pgg_agent_loop_event_ledger.jsonl"
_MAX_LINES_BYTES = 8192


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def _stable_hash(value: Any) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        raw = repr(value)
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()


def _arg_shape(args: Any) -> dict[str, Any]:
    """Return non-secret argument shape, never raw values."""
    if isinstance(args, Mapping):
        keys = sorted(str(k) for k in args.keys())[:50]
        return {"kind": "object", "keys": keys, "sha256": _stable_hash(args)}
    if isinstance(args, (list, tuple)):
        return {"kind": "array", "len": len(args), "sha256": _stable_hash(args)}
    if args is None:
        return {"kind": "null", "sha256": _stable_hash(args)}
    return {"kind": type(args).__name__, "sha256": _stable_hash(args)}


def append_agent_loop_event(event_type: str, **fields: Any) -> None:
    """Append one compact event. Fail-open and never raise."""
    try:
        if event_type not in _ALLOWED_TYPES:
            event_type = "stream_event"
        data_dir = _hermes_home() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "schema": "PGGAgentLoopEvent/v1",
            "type": event_type,
            "timestamp": time.time(),
            "session_id": str(fields.get("session_id") or ""),
            "task_id": fields.get("task_id") or None,
            "turn_id": fields.get("turn_id") or None,
            "step_id": fields.get("step_id") or None,
            "phase_id": fields.get("phase_id") or None,
            "model": fields.get("model") or None,
            "provider": fields.get("provider") or None,
            "tool_name": fields.get("tool_name") or None,
            "tool_call_id": fields.get("tool_call_id") or None,
            "api_request_id": fields.get("api_request_id") or None,
            "status": fields.get("status") or "observed",
            "usage": fields.get("usage") or {},
            "cost_usd": fields.get("cost_usd") if fields.get("cost_usd") is not None else None,
            "boundary": fields.get("boundary") or "PGGAgentLoopEvent ledger; metadata/hash only; no raw args/results/secrets",
        }
        if "args" in fields:
            payload["args_shape"] = _arg_shape(fields.get("args"))
        if "summary_material" in fields:
            payload["summary_hash"] = _stable_hash(fields.get("summary_material"))
        for key in (
            "before_tokens", "after_tokens", "before_messages", "after_messages", "old_session_id", "new_session_id", "lossy",
            "result_subtype", "api_calls", "max_turns", "turn_exit_reason", "completed", "failed", "partial", "interrupted",
        ):
            if key in fields:
                payload[key] = fields.get(key)
        if "budget" in fields and isinstance(fields.get("budget"), Mapping):
            allowed_budget = {"max_turns", "max_wall_seconds", "max_budget_usd", "max_tool_calls", "max_write_ops", "budget_used", "budget_max"}
            payload["budget"] = {str(k): v for k, v in fields.get("budget", {}).items() if str(k) in allowed_budget}
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        if len(line.encode("utf-8", "replace")) > _MAX_LINES_BYTES:
            payload.pop("args_shape", None)
            payload["truncated"] = True
            line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        with (data_dir / _LEDGER_NAME).open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        return
