#!/usr/bin/env python3
"""Read-only observability ledger for PGGAgentLoopEvent/v1.

Writes compact, credential-safe event metadata for Exec Dashboard aggregation.
No provider/config/scheduler/security mutation. Fail-open by design.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

_ALLOWED_TYPES = {"tool_request", "tool_result", "compact_boundary", "loop_result", "stream_event"}
_LEDGER_NAME = "pgg_agent_loop_event_ledger.jsonl"
_MAX_LINES_BYTES = 8192
_LOCAL_HMAC_ENV = "HERMES_AGENT_LOOP_LEDGER_HMAC_KEY"


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def _ledger_hmac_key() -> bytes:
    """Return local-only HMAC key material without logging or exporting it."""
    configured = os.environ.get(_LOCAL_HMAC_ENV)
    if configured:
        return configured.encode("utf-8", "replace")
    # Deterministic per-install fallback.  This keeps dashboard joins stable on
    # the same machine while avoiding bare unsalted hashes of sensitive inputs.
    return str(_hermes_home()).encode("utf-8", "replace") + b"\0pgg-agent-loop-ledger-v1"


def _stable_hmac(value: Any) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        raw = repr(value)
    return hmac.new(_ledger_hmac_key(), raw.encode("utf-8", "replace"), hashlib.sha256).hexdigest()


def _id_fingerprint(value: Any) -> dict[str, Any]:
    """Return a non-reversible identifier fingerprint for observability joins."""
    raw = str(value or "")
    return {"present": bool(raw), "hmac_sha256": _stable_hmac(raw), "length": len(raw)}


def _arg_shape(args: Any) -> dict[str, Any]:
    """Return non-secret argument shape, never raw values."""
    if isinstance(args, Mapping):
        keys = sorted(str(k) for k in args.keys())[:50]
        return {"kind": "object", "key_count": len(keys), "keys_hmac_sha256": _stable_hmac(keys), "hmac_sha256": _stable_hmac(args)}
    if isinstance(args, (list, tuple)):
        return {"kind": "array", "len": len(args), "hmac_sha256": _stable_hmac(args)}
    if args is None:
        return {"kind": "null", "hmac_sha256": _stable_hmac(args)}
    return {"kind": type(args).__name__, "hmac_sha256": _stable_hmac(args)}


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
            "session_ref": _id_fingerprint(fields.get("session_id")),
            "task_ref": _id_fingerprint(fields.get("task_id")),
            "turn_ref": _id_fingerprint(fields.get("turn_id")),
            "step_ref": _id_fingerprint(fields.get("step_id")),
            "phase_ref": _id_fingerprint(fields.get("phase_id")),
            "model_ref": _id_fingerprint(fields.get("model")),
            "provider_ref": _id_fingerprint(fields.get("provider")),
            "tool_name_ref": _id_fingerprint(fields.get("tool_name")),
            "tool_call_ref": _id_fingerprint(fields.get("tool_call_id")),
            "api_request_ref": _id_fingerprint(fields.get("api_request_id")),
            "status": fields.get("status") or "observed",
            "usage_shape": _arg_shape(fields.get("usage") or {}),
            "cost_usd": fields.get("cost_usd") if fields.get("cost_usd") is not None else None,
            "boundary": fields.get("boundary") or "PGGAgentLoopEvent ledger; metadata/hash only; no raw args/results/credential values",
        }
        if "args" in fields:
            payload["args_shape"] = _arg_shape(fields.get("args"))
        if "summary_material" in fields:
            payload["summary_hmac_sha256"] = _stable_hmac(fields.get("summary_material"))
        for key in (
            "before_tokens", "after_tokens", "before_messages", "after_messages", "lossy",
            "result_subtype", "api_calls", "max_turns", "turn_exit_reason", "completed", "failed", "partial", "interrupted",
            "error_type",
        ):
            if key in fields:
                payload[key] = fields.get(key)
        for key in ("old_session_id", "new_session_id"):
            if key in fields:
                payload[key.replace("_id", "_ref")] = _id_fingerprint(fields.get(key))
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
