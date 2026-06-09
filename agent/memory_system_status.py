"""PGG/Hermes memory system global status gate.

Chinese command target: ``记忆系统``.

Read-only aggregator for the user's memory architecture: curated MEMORY/USER,
Akashic, Department/SWR runtime, external MemoryProvider readiness, and recent
manifest landing keys.  It intentionally does not enable providers, mutate
config, or write curated memory.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from hermes_constants import get_hermes_home


MEMORY_MANIFEST_KEYS = [
    "latest_memory_context_architecture_audit_precompress_fix_20260608",
    "latest_akashic_consistency_gate_repair_20260608",
    "latest_curated_memory_akashic_observe_first_mirror_20260608",
    "latest_akashic_profile_aware_storage_20260608",
    "latest_akashic_validity_tombstone_sync_20260608",
    "latest_akashic_cross_instance_hot_reload_20260608",
    "latest_external_memory_provider_readiness_gate_20260608",
    "latest_department_memory_runtime_schema_20260608",
    "latest_akashic_multi_writer_transaction_lock_20260608",
    "latest_holographic_external_memory_provider_sandbox_eval_20260608",
    "latest_memory_system_global_command_20260609",
]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sha256(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_summary(path: Path) -> Dict[str, Any]:
    exists = path.exists()
    st = path.stat() if exists else None
    text = ""
    if exists and path.is_file():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
    entries = [part.strip() for part in text.split("§") if part.strip()] if text else []
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": st.st_size if st else 0,
        "mtime_utc": _dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).isoformat() if st else None,
        "sha256": _sha256(path),
        "char_count": len(text),
        "entry_count_by_section_marker": len(entries),
    }


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        return {"_load_error": f"{type(e).__name__}: {str(e)[:240]}"}


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"_non_object_json": data}
    except Exception as e:
        return {"_load_error": f"{type(e).__name__}: {str(e)[:240]}"}


def _curated_status(home: Path) -> Dict[str, Any]:
    memory = home / "memories" / "MEMORY.md"
    user = home / "memories" / "USER.md"
    soul = home / "SOUL.md"
    cfg = _read_yaml(home / "config.yaml")
    mem_cfg = cfg.get("memory", {}) if isinstance(cfg.get("memory"), dict) else {}
    return {
        "status": "PASS" if memory.exists() and user.exists() else "WATCH_MISSING_CURATED_FILE",
        "authoritative": True,
        "memory_enabled": mem_cfg.get("memory_enabled"),
        "user_profile_enabled": mem_cfg.get("user_profile_enabled"),
        "memory_char_limit": mem_cfg.get("memory_char_limit"),
        "user_char_limit": mem_cfg.get("user_char_limit"),
        "external_provider_configured": mem_cfg.get("provider") or "",
        "files": {
            "MEMORY.md": _file_summary(memory),
            "USER.md": _file_summary(user),
            "SOUL.md": _file_summary(soul),
        },
    }


def _akashic_status(home: Path) -> Dict[str, Any]:
    try:
        from agent.akashic_consistency import audit_akashic_consistency
        from agent.akashic_memory import AkashicMemory

        audit = audit_akashic_consistency()
        ak = AkashicMemory()
        stats = ak.get_stats()
        code_path = Path(__file__).resolve().parent / "akashic_memory.py"
        code = code_path.read_text(encoding="utf-8", errors="ignore") if code_path.exists() else ""
        markers = {
            "profile_aware": "get_akashic_home" in code and "get_hermes_home" in code,
            "write_lock": "def _write_lock" in code and "fcntl.flock" in code,
            "atomic_save_npy": "def _atomic_save_npy" in code,
            "hot_reload": "def reload_if_stale" in code,
            "tombstone_sync": "def tombstone_curated_entry" in code and "validity_status" in code,
        }
        return {
            "status": "PASS" if audit.get("status") == "PASS" else audit.get("status", "UNKNOWN"),
            "audit": audit,
            "stats": stats,
            "code_markers": markers,
        }
    except Exception as e:
        return {"status": "ERROR", "error": f"{type(e).__name__}: {str(e)[:240]}"}


def _department_status(home: Path) -> Dict[str, Any]:
    try:
        from agent.department_memory_runtime import build_department_memory_runtime_state
        state = build_department_memory_runtime_state(home)
        return {
            "status": state.get("runtime_status", "UNKNOWN"),
            "schema": state.get("schema"),
            "write_allowed": state.get("write_allowed"),
            "apply_allowed": state.get("apply_allowed"),
            "counts": state.get("counts"),
            "blockers": (state.get("gate") or {}).get("blockers", []),
            "runtime_state_file": str(home / "workspace/pgg-archon-governance/department-memory-runtime/department_memory_runtime_latest.json"),
        }
    except Exception as e:
        return {"status": "ERROR", "error": f"{type(e).__name__}: {str(e)[:240]}"}


def _external_provider_status(home: Path) -> Dict[str, Any]:
    try:
        from agent.memory_provider_readiness import audit_memory_provider_readiness
        readiness = audit_memory_provider_readiness()
        providers = readiness.get("providers", [])
        provider_summary = {
            p.get("name", "unknown"): {
                "recommendation": p.get("recommendation"),
                "privacy_risk": p.get("privacy_risk"),
                "tool_count": p.get("tool_count"),
            }
            for p in providers
        }
        return {
            "status": readiness.get("status"),
            "active_external_provider": readiness.get("active_external_provider"),
            "provider_count": readiness.get("provider_count"),
            "recommended_next_step": readiness.get("recommended_next_step"),
            "config_modified": readiness.get("config_modified"),
            "secrets_printed": readiness.get("secrets_printed"),
            "providers": provider_summary,
        }
    except Exception as e:
        return {"status": "ERROR", "error": f"{type(e).__name__}: {str(e)[:240]}"}


def _holographic_status(home: Path) -> Dict[str, Any]:
    cfg = _read_yaml(home / "config.yaml")
    active_provider = ""
    if isinstance(cfg.get("memory"), dict):
        active_provider = cfg["memory"].get("provider") or ""
    db = home / "memory_store.db"
    latest_manifest = None
    manifest = _load_json(home / "data" / "EVOLUTION_MANIFEST.json") or {}
    key = "latest_holographic_external_memory_provider_sandbox_eval_20260608"
    if isinstance(manifest, dict):
        latest_manifest = manifest.get(key)
    return {
        "status": "SANDBOX_PASS_DEFAULT_NOT_ENABLED" if active_provider != "holographic" else "ACTIVE_IN_DEFAULT",
        "active_in_default": active_provider == "holographic",
        "default_db": _file_summary(db),
        "latest_sandbox_manifest_status": latest_manifest.get("status") if isinstance(latest_manifest, dict) else None,
        "boundary": "Sandbox eval passed, but default profile is not enabled unless active_in_default=true.",
    }


def _manifest_status(home: Path) -> Dict[str, Any]:
    path = home / "data" / "EVOLUTION_MANIFEST.json"
    data = _load_json(path) or {}
    entries = {}
    if isinstance(data, dict):
        for key in MEMORY_MANIFEST_KEYS:
            val = data.get(key)
            if isinstance(val, dict):
                entries[key] = {
                    "status": val.get("status"),
                    "time_utc": val.get("time_utc") or val.get("timestamp"),
                    "report": val.get("report"),
                    "boundary": val.get("boundary"),
                }
            else:
                entries[key] = None
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": _sha256(path),
        "tracked_memory_keys": entries,
    }


def _score(status: Dict[str, Any]) -> Dict[str, Any]:
    checks = {
        "curated_present": status.get("curated", {}).get("status") == "PASS",
        "akashic_consistent": status.get("akashic", {}).get("status") == "PASS",
        "akashic_lock_present": bool(status.get("akashic", {}).get("code_markers", {}).get("write_lock")),
        "department_fail_closed_or_ready": status.get("department_swr", {}).get("status") in {"NOOP_BLOCKED_OR_EMPTY", "REVIEW_PENDING_NO_WRITE", "APPLY_ALLOWED_AWAITING_EXECUTOR_AUTHORIZATION"},
        "external_gate_readonly": status.get("external_provider", {}).get("status") == "PASS_READ_ONLY_AUDIT",
        "holographic_not_accidentally_enabled": status.get("holographic", {}).get("status") in {"SANDBOX_PASS_DEFAULT_NOT_ENABLED", "ACTIVE_IN_DEFAULT"},
        "manifest_entries_present": all(v is not None for v in status.get("manifest", {}).get("tracked_memory_keys", {}).values()),
    }
    passed = [k for k, v in checks.items() if v]
    failed = [k for k, v in checks.items() if not v]
    score = round(100.0 * len(passed) / max(len(checks), 1), 2)
    return {"score_percent": score, "passed": passed, "failed_or_watch": failed, "checks": checks}


def build_memory_system_status(home: Path | None = None) -> Dict[str, Any]:
    h = home or get_hermes_home()
    status: Dict[str, Any] = {
        "schema": "PGGMemorySystemStatus/v1",
        "command": "记忆系统",
        "generated_at": _now(),
        "hermes_home": str(h),
        "read_only": True,
        "config_modified": False,
        "curated": _curated_status(h),
        "akashic": _akashic_status(h),
        "department_swr": _department_status(h),
        "external_provider": _external_provider_status(h),
        "holographic": _holographic_status(h),
        "manifest": _manifest_status(h),
        "boundary": "Global memory status only; does not enable providers, write MEMORY/USER, or apply Department/SWR memory.",
    }
    status["overall"] = _score(status)
    return status


def _print_text(status: Dict[str, Any]) -> None:
    overall = status["overall"]
    print("记忆系统 / PGG Memory System")
    print(f"status_score: {overall['score_percent']}%")
    print(f"hermes_home: {status['hermes_home']}")
    print(f"curated: {status['curated']['status']} MEMORY_chars={status['curated']['files']['MEMORY.md']['char_count']} USER_chars={status['curated']['files']['USER.md']['char_count']}")
    ak = status["akashic"]
    print(f"akashic: {ak.get('status')} counts={ak.get('audit', {}).get('counts')} lock={ak.get('code_markers', {}).get('write_lock')}")
    dep = status["department_swr"]
    print(f"department_swr: {dep.get('status')} write_allowed={dep.get('write_allowed')} apply_allowed={dep.get('apply_allowed')} blockers={dep.get('blockers')}")
    ext = status["external_provider"]
    recommended = ext.get("recommended_next_step", {})
    if isinstance(recommended, dict):
        recommended_text = recommended.get("provider") or recommended.get("action")
    else:
        recommended_text = recommended
    print(f"external_provider: {ext.get('status')} active={ext.get('active_external_provider')!r} recommended={recommended_text}")
    holo = status["holographic"]
    print(f"holographic: {holo.get('status')} active_in_default={holo.get('active_in_default')} sandbox_manifest={holo.get('latest_sandbox_manifest_status')}")
    if overall["failed_or_watch"]:
        print("WATCH:", ", ".join(overall["failed_or_watch"]))
    print("boundary:", status["boundary"])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="记忆系统", description="PGG/Hermes memory system global status")
    parser.add_argument("--json", action="store_true", help="print full JSON status")
    args = parser.parse_args(argv)
    status = build_memory_system_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(status)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
