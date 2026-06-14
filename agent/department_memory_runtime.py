"""PGG Department/SWR memory first-class runtime schema.

Consolidates the legacy SWR/team/department memory pipeline artifacts into a
single runtime state document.  This module does not approve or apply memory
writes.  Its purpose is to make the department memory subsystem observable and
machine-verifiable instead of a loose chain of scripts and JSON files.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from hermes_constants import get_hermes_home


SCHEMA = "PGGDepartmentMemoryRuntime/v1"
DEPARTMENTS = [
    "hub",
    "cms",
    "evidence",
    "legal_support",
    "civil",
    "criminal",
    "inspection",
    "audit",
    "knowledge",
]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _json_load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"_non_object_json": data}
    except Exception as e:
        return {"_load_error": f"{type(e).__name__}: {str(e)[:240]}"}


def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_summary(path: Path) -> Dict[str, Any]:
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": stat.st_size if stat else 0,
        "mtime_utc": _dt.datetime.fromtimestamp(stat.st_mtime, _dt.timezone.utc).isoformat() if stat else None,
        "sha256": _sha256_file(path) if exists and path.is_file() else None,
    }


def _latest_ledger_line(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "line_count": 0, "latest": None, "load_error": None}
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        latest = None
        if lines:
            try:
                latest = json.loads(lines[-1])
            except Exception:
                latest = {"raw": lines[-1][:500]}
        return {"path": str(path), "exists": True, "line_count": len(lines), "latest": latest, "load_error": None}
    except Exception as e:
        return {"path": str(path), "exists": True, "line_count": 0, "latest": None, "load_error": f"{type(e).__name__}: {e}"}


def _generated_at(obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    val = obj.get("generated_at") or obj.get("ts")
    return str(val) if val else None


def _staleness_seconds(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        dt = _dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return max(0.0, (_dt.datetime.now(_dt.timezone.utc) - dt).total_seconds())
    except Exception:
        return None


def _department_counts(items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = {d: 0 for d in DEPARTMENTS}
    counts["unknown"] = 0
    for item in items:
        dept = str(item.get("department") or "unknown")
        counts[dept if dept in counts else "unknown"] += 1
    return counts


def _safe_target(path: Any, safe_root: Path) -> bool:
    if not path:
        return True
    try:
        p = Path(str(path)).expanduser().resolve(strict=False)
        root = safe_root.resolve(strict=False)
        return str(p).startswith(str(root)) and ".." not in Path(str(path)).parts
    except Exception:
        return False


def build_department_memory_runtime_state(hermes_home: Path | None = None) -> Dict[str, Any]:
    """Build a consolidated runtime state document without mutating memory."""
    h = hermes_home or get_hermes_home()
    out = h / "workspace/pgg-archon-governance/team-memory-p3-20260606"
    safe_root = h / "workspace/pgg-archon-governance/department-memory"

    paths = {
        "distillation": out / "department_memory_distillation_latest.json",
        "review_desk": out / "department_memory_review_desk_latest.json",
        "apply_request": out / "department_memory_apply_request_latest.json",
        "rollback_package": out / "department_memory_rollback_package_latest.json",
        "review_gate": out / "department_memory_review_gate_result.json",
        "distillation_gate": out / "department_memory_distillation_gate_result.json",
        "apply_gate": out / "department_memory_apply_gate_result.json",
        "apply_executor": out / "department_memory_apply_executor_latest.json",
    }
    ledgers = {
        "distillation": h / "data/pgg-background-evolution/pgg_department_memory_distillation_ledger.jsonl",
        "review_desk": h / "data/pgg-background-evolution/pgg_department_memory_review_desk_ledger.jsonl",
        "apply_gate": h / "data/pgg-background-evolution/pgg_department_memory_apply_gate_ledger.jsonl",
    }

    loaded = {name: _json_load(path) for name, path in paths.items()}
    dist = loaded.get("distillation") or {}
    desk = loaded.get("review_desk") or {}
    apply_req = loaded.get("apply_request") or {}
    rollback = loaded.get("rollback_package") or {}
    apply_gate = loaded.get("apply_gate") or {}
    executor = loaded.get("apply_executor") or {}

    dist_records = dist.get("records", []) if isinstance(dist.get("records"), list) else []
    apply_items = apply_req.get("items", []) if isinstance(apply_req.get("items"), list) else []
    desk_items = desk.get("items", []) if isinstance(desk.get("items"), list) else []
    rollback_items = rollback.get("rollback_items", []) if isinstance(rollback.get("rollback_items"), list) else []

    unsafe_targets = [
        str(i.get("target_path"))
        for i in apply_items
        if not _safe_target(i.get("target_path"), safe_root)
    ]
    pending_reviews = [
        i.get("review_id") or i.get("source_sha256")
        for i in desk_items
        if i.get("department_review") == "PENDING" or i.get("central_audit") == "PENDING"
    ]
    approved_apply_items = [
        i for i in apply_items
        if i.get("department_review") == "PASS" and i.get("central_audit") == "PASS" and i.get("distilled") is True
    ]

    apply_gate_obj = apply_gate.get("gate", {}) if isinstance(apply_gate, dict) else {}
    apply_allowed = bool(apply_gate_obj.get("apply_allowed"))
    executor_status = str(executor.get("status") or executor.get("result") or "unknown") if isinstance(executor, dict) else "unknown"

    generated_times = {k: _generated_at(v) for k, v in loaded.items()}
    stale = {k: _staleness_seconds(v) for k, v in generated_times.items()}

    readiness_checks = {
        "artifacts_present": all((loaded.get(k) is not None and "_load_error" not in (loaded.get(k) or {})) for k in ["distillation", "review_desk", "apply_request", "apply_gate"]),
        "safe_targets": not unsafe_targets,
        "no_pending_unapproved_write": not approved_apply_items or apply_allowed,
        "user_authorization_present": bool(apply_req.get("user_authorization") and apply_req.get("authorization_scope") == "department_memory_apply"),
        "rollback_package_present": bool(rollback_items),
        "review_queue_empty_or_pending_only": all(i.get("write_allowed") is False for i in desk_items),
        "executor_no_apply_without_gate": not ("applied" in executor_status.lower() and not apply_allowed),
    }

    if apply_allowed:
        runtime_status = "APPLY_ALLOWED_AWAITING_EXECUTOR_AUTHORIZATION"
    elif approved_apply_items:
        runtime_status = "BLOCKED_APPROVED_ITEMS_BUT_GATE_CLOSED"
    elif desk_items:
        runtime_status = "REVIEW_PENDING_NO_WRITE"
    else:
        runtime_status = "NOOP_BLOCKED_OR_EMPTY"

    blockers: List[str] = []
    if not readiness_checks["artifacts_present"]:
        blockers.append("missing_or_invalid_core_artifacts")
    if unsafe_targets:
        blockers.append("unsafe_target_path")
    if not readiness_checks["user_authorization_present"]:
        blockers.append("no_department_memory_apply_authorization")
    if not rollback_items:
        blockers.append("rollback_package_empty_or_absent")
    if not apply_allowed:
        blockers.append("apply_gate_closed")

    state = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "hermes_home": str(h),
        "runtime_status": runtime_status,
        "write_allowed": False,
        "apply_allowed": apply_allowed,
        "curated_memory_authoritative": True,
        "external_memory_provider_required": False,
        "departments": DEPARTMENTS,
        "counts": {
            "distillation_candidate_count": int(dist.get("candidate_count") or len(dist_records) or 0),
            "distilled_count": int(dist.get("distilled_count") or len([r for r in dist_records if r.get("distillation_status") == "distilled"])),
            "archived_count": int(dist.get("archived_count") or len([r for r in dist_records if r.get("distillation_status") != "distilled"])),
            "review_candidate_count": int(desk.get("candidate_count") or len(desk_items) or 0),
            "apply_item_count": len(apply_items),
            "approved_apply_item_count": len(approved_apply_items),
            "rollback_item_count": len(rollback_items),
        },
        "department_counts": {
            "distillation_records": _department_counts([r for r in dist_records if isinstance(r, dict)]),
            "review_items": _department_counts([i for i in desk_items if isinstance(i, dict)]),
            "apply_items": _department_counts([i for i in apply_items if isinstance(i, dict)]),
        },
        "gate": {
            "apply_gate_status": apply_gate_obj.get("status"),
            "apply_gate_score_percent": apply_gate_obj.get("score_percent"),
            "apply_gate_missing_checks": apply_gate_obj.get("missing_checks", []),
            "apply_executor_status": executor_status,
            "readiness_checks": readiness_checks,
            "blockers": blockers,
            "unsafe_targets": unsafe_targets,
            "pending_reviews": pending_reviews,
        },
        "freshness": {
            "generated_times": generated_times,
            "staleness_seconds": stale,
            "note": "Freshness is advisory; each source artifact remains authoritative for its own gate.",
        },
        "artifacts": {name: _file_summary(path) for name, path in paths.items()},
        "ledgers": {name: _latest_ledger_line(path) for name, path in ledgers.items()},
        "boundary": (
            "Runtime schema only. It does not approve, apply, or write MEMORY/USER/SKILL/case files. "
            "Real writes still require distilled candidate, department PASS, central audit PASS, explicit user authorization, rollback preimage, safe path, Rust apply gate allow, and executor --apply."
        ),
    }
    return state


def write_runtime_state(state: Dict[str, Any], hermes_home: Path | None = None) -> Path:
    h = hermes_home or get_hermes_home()
    out_dir = h / "workspace/pgg-archon-governance/department-memory-runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "department_memory_runtime_latest.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(out)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="PGG department memory runtime schema gate")
    parser.add_argument("--write-state", action="store_true", help="write runtime state JSON under workspace")
    args = parser.parse_args(argv)
    state = build_department_memory_runtime_state()
    if args.write_state:
        out = write_runtime_state(state)
        state["runtime_state_file"] = str(out)
    print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
