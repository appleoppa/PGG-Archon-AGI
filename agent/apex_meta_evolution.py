"""APEX RuntimeOS meta-evolution evidence reports.

This module composes existing read-only RuntimeOS surfaces into a compact
meta-evolution report: strategy ledger, shadow replay, drift sensor, and cost
sensor. It does not promote genes, mutate memory/skills, or claim AGI completion.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping

_DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "workspace" / "meta_evolution"


def _safe_text(value: Any, *, limit: int = 240) -> str:
    text = str(value or "").replace("\r", " ").strip()
    lower = text.lower()
    if any(marker in lower for marker in ("api_key", "authorization:", "bearer ", "password", "secret=", "token=")):
        return "[REDACTED]"
    if "/Users/" in text or "\\Users\\" in text:
        return text.replace("/Users/", "[REDACTED_PATH]/").replace("\\Users\\", "[REDACTED_PATH]\\")[:limit]
    return text[:limit]


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_workspace_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("Meta-evolution report path must stay under repository workspace") from exc
    if resolved.is_symlink():
        raise ValueError("Meta-evolution report path must not be a symlink")
    return resolved


def _safe_report_dir(path: Path | None = None) -> Path:
    resolved = (path or _DEFAULT_REPORT_DIR).expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("Meta-evolution report directory must stay under repository workspace") from exc
    return resolved


def build_meta_evolution_report(status: Mapping[str, Any]) -> Dict[str, Any]:
    cron = _as_mapping(status.get("cron_dryrun"))
    flow = _as_mapping(status.get("flow_reward_report"))
    switch = _as_mapping(status.get("switch_cost_report"))
    era = _as_mapping(status.get("era_report"))
    co = _as_mapping(status.get("co_scientist_report"))
    health = _as_mapping(status.get("health_report"))
    quality = _as_mapping(status.get("quality_gate"))
    cron_tasks = cron.get("tasks") if isinstance(cron.get("tasks"), Mapping) else {}
    flow_valid = bool(flow.get("valid")) and _status(flow.get("status")) in {"PASS", "WATCH"}
    switch_observed = bool(switch.get("valid")) and _status(switch.get("status")) in {"PASS", "WATCH", "HOLD"}
    cron_cost_observed = int(cron.get("total_lines") or 0) > 0 and isinstance(cron_tasks, Mapping)
    signals = {
        "strategy_ledger": int(cron.get("unique_keys") or 0) > 0 and int(cron.get("bad_lines") or 0) == 0,
        "shadow_replay": flow_valid and bool(flow.get("selected_path_id")),
        "drift_sensor": flow_valid and "score_delta" in flow,
        "cost_sensor": switch_observed or cron_cost_observed,
        "era_feedback_bound": bool(era.get("selected_path_id")) and bool(flow.get("selected_path_id")),
        "co_scientist_bound": _status(co.get("status")) == "PASS",
        "quality_feedback_bound": _status(quality.get("status")) == "PASS" or _status(health.get("status")) in {"OK", "INFO"},
    }
    score = round(100 * sum(1 for ok in signals.values() if ok) / len(signals), 1)
    if score >= 80:
        report_status = "PASS"
    elif score >= 60:
        report_status = "WATCH"
    else:
        report_status = "HOLD"
    return {
        "schema": "ApexMetaEvolutionReport/v1",
        "ts": time.time(),
        "status": report_status,
        "score": score,
        "signals": signals,
        "missing": [key for key, ok in signals.items() if not ok],
        "strategy_ledger": {
            "valid": signals["strategy_ledger"],
            "unique_keys": int(cron.get("unique_keys") or 0),
            "bad_lines": int(cron.get("bad_lines") or 0),
            "ledger_source": "cron_dryrun_read_only",
        },
        "shadow_replay": {
            "valid": signals["shadow_replay"],
            "flow_status": _safe_text(flow.get("status"), limit=40),
            "selected_path_id": _safe_text(flow.get("selected_path_id"), limit=80),
            "realized_score": float(flow.get("realized_score") or 0.0),
            "mode": "read_only_shadow_observation",
        },
        "drift_sensor": {
            "valid": signals["drift_sensor"],
            "score_delta": float(flow.get("score_delta") or 0.0),
            "mode": "flow_reward_delta_read_only",
        },
        "cost_sensor": {
            "valid": signals["cost_sensor"],
            "switch_status": _safe_text(switch.get("status"), limit=40),
            "net_gain": float(switch.get("net_gain") or 0.0),
            "cron_total_lines": int(cron.get("total_lines") or 0),
            "cron_task_count": len(cron_tasks) if isinstance(cron_tasks, Mapping) else 0,
            "mode": "switch_cost_or_cron_activity_read_only",
        },
        "llm_validator": {
            "valid": True,
            "role": "inner_reasoning_validator_only",
            "boundary": "LLM review can propose engineering fixes but cannot mark external code trusted or complete AGI.",
        },
        "side_effects": "read_only_report",
        "agi_completion_claim": False,
    }


def summarize_meta_evolution_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "ApexMetaEvolutionSummary/v1",
        "valid": report.get("schema") == "ApexMetaEvolutionReport/v1",
        "status": _safe_text(report.get("status"), limit=40),
        "score": float(report.get("score") or 0.0),
        "missing": list(report.get("missing") or [])[:8] if isinstance(report.get("missing"), list) else [],
        "side_effects": "read_only_report",
        "agi_completion_claim": False,
    }


def write_meta_evolution_report(path: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    safe_path = _safe_workspace_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(safe_path), "schema": report.get("schema")}


def default_meta_evolution_report_path(task: str = "meta_evolution") -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in task)[:80] or "meta_evolution"
    return _DEFAULT_REPORT_DIR / f"{int(time.time())}_{safe}.json"


def load_latest_meta_evolution_report(directory: Path | None = None) -> Dict[str, Any] | None:
    root = _safe_report_dir(directory)
    if not root.exists():
        return None
    candidates = [item for item in root.glob("*.json") if item.is_file() and not item.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: (item.stat().st_mtime, item.name))
    data = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Meta-evolution report must be a mapping")
    return summarize_meta_evolution_report(data)


__all__ = [
    "build_meta_evolution_report",
    "default_meta_evolution_report_path",
    "load_latest_meta_evolution_report",
    "summarize_meta_evolution_report",
    "write_meta_evolution_report",
]
