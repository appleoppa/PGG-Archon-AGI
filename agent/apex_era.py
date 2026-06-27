"""APEX ERA read-only path search reports.

ERA is the exploration layer: it records alternative execution paths, scores
low-risk/high-evidence options, and exposes a compact decision report.  It never
executes a path, mutates runtime state, or promotes genes/skills by itself.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

_MAX_TEXT = 600
_DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "workspace" / "era_path_search"


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = str(value or "").replace("\r", " ").strip()
    lower = text.lower()
    if any(marker in lower for marker in ("api_key", "authorization:", "bearer ", "password", "secret=")):
        return "[REDACTED]"
    if "/Users/" in text or "\\Users\\" in text:
        return text.replace("/Users/", "[REDACTED_PATH]/").replace("\\Users\\", "[REDACTED_PATH]\\")[:limit]
    return text[:limit]


def _safe_workspace_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("ERA report path must stay under repository workspace") from exc
    if resolved.is_symlink():
        raise ValueError("ERA report path must not be a symlink")
    return resolved


def _safe_report_dir(path: Path | None = None) -> Path:
    resolved = (path or _DEFAULT_REPORT_DIR).expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("ERA report directory must stay under repository workspace") from exc
    return resolved


def _score_path(path: Mapping[str, Any]) -> float:
    reward = float(path.get("reward") or path.get("benefit") or 0.0)
    evidence = float(path.get("evidence") or path.get("verification") or 0.0)
    confidence = float(path.get("confidence") or 0.0)
    risk = float(path.get("risk") or 0.0)
    cost = float(path.get("cost") or 0.0)
    uncertainty = float(path.get("uncertainty") or 0.0)
    raw = (reward * 0.35) + (evidence * 0.30) + (confidence * 0.20) - (risk * 0.30) - (cost * 0.10) - (uncertainty * 0.10)
    return round(max(0.0, min(1.0, raw)), 4)


def build_era_path_search_report(
    *,
    task: str,
    paths: Sequence[Mapping[str, Any]],
    source: str = "apex-runtimeos-era",
) -> Dict[str, Any]:
    """Build a sanitized, read-only ERA path search report."""
    sanitized_paths = []
    for idx, raw in enumerate(paths):
        actions_raw = raw.get("actions")
        actions = actions_raw if isinstance(actions_raw, list) else []
        item = {
            "id": _safe_text(raw.get("id") or f"path-{idx + 1}", limit=80),
            "title": _safe_text(raw.get("title"), limit=160),
            "summary": _safe_text(raw.get("summary")),
            "actions": [_safe_text(action, limit=160) for action in actions[:8]],
            "risk": float(raw.get("risk") or 0.0),
            "cost": float(raw.get("cost") or 0.0),
            "reward": float(raw.get("reward") or raw.get("benefit") or 0.0),
            "evidence": float(raw.get("evidence") or raw.get("verification") or 0.0),
            "confidence": float(raw.get("confidence") or 0.0),
            "uncertainty": float(raw.get("uncertainty") or 0.0),
            "side_effects": "not_executed",
        }
        item["score"] = _score_path(item)
        sanitized_paths.append(item)
    ranked = sorted(sanitized_paths, key=lambda item: (float(item.get("score") or 0.0), -float(item.get("risk") or 0.0), item.get("id", "")), reverse=True)
    selected = ranked[0] if ranked else None
    status = "PASS" if selected and float(selected.get("score") or 0.0) >= 0.5 else ("WATCH" if ranked else "BLOCK")
    return {
        "schema": "ApexERAPathSearchReport/v1",
        "ts": time.time(),
        "source": _safe_text(source, limit=120),
        "task": _safe_text(task, limit=240),
        "path_count": len(ranked),
        "status": status,
        "selected_path_id": selected.get("id") if selected else "",
        "selected_score": selected.get("score") if selected else 0.0,
        "paths": ranked[:8],
        "side_effects": "read_only_report",
        "executed": False,
        "promotion_required": True,
    }


def summarize_era_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "ApexERAPathSearchSummary/v1",
        "valid": report.get("schema") == "ApexERAPathSearchReport/v1",
        "status": _safe_text(report.get("status"), limit=40),
        "task": _safe_text(report.get("task"), limit=160),
        "path_count": int(report.get("path_count") or 0) if isinstance(report.get("path_count"), int) else 0,
        "selected_path_id": _safe_text(report.get("selected_path_id"), limit=80),
        "selected_score": float(report.get("selected_score") or 0.0),
        "executed": bool(report.get("executed")),
        "promotion_required": bool(report.get("promotion_required")),
        "side_effects": "read_only_report",
    }


def write_era_report(path: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    safe_path = _safe_workspace_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(safe_path), "schema": report.get("schema")}


def default_era_report_path(task: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in task)[:80] or "era_path_search"
    return _DEFAULT_REPORT_DIR / f"{int(time.time())}_{safe}.json"


def load_latest_era_report(directory: Path | None = None) -> Dict[str, Any] | None:
    root = _safe_report_dir(directory)
    if not root.exists():
        return None
    candidates = [item for item in root.glob("*.json") if item.is_file() and not item.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: (item.stat().st_mtime, item.name))
    data = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ERA report must be a mapping")
    return summarize_era_report(data)


__all__ = [
    "build_era_path_search_report",
    "default_era_report_path",
    "load_latest_era_report",
    "summarize_era_report",
    "write_era_report",
]
