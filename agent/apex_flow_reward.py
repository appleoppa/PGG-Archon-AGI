"""APEX Flow reward feedback reports.

Flow reward is the post-choice feedback layer: it compares a selected execution
path with observed outcome signals, computes a compact fitness score, and keeps a
read-only audit trail for future routing.  It never executes paths, mutates model
state, or promotes genes/skills by itself.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

_MAX_TEXT = 600
_DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "workspace" / "flow_reward"


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = str(value or "").replace("\r", " ").strip()
    lower = text.lower()
    if any(marker in lower for marker in ("api_key", "authorization:", "bearer ", "password", "secret=")):
        return "[REDACTED]"
    if "/Users/" in text or "\\Users\\" in text:
        return text.replace("/Users/", "[REDACTED_PATH]/").replace("\\Users\\", "[REDACTED_PATH]\\")[:limit]
    return text[:limit]


def _safe_report_dir(path: Path | None = None) -> Path:
    resolved = (path or _DEFAULT_REPORT_DIR).expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("Flow reward report directory must stay under repository workspace") from exc
    return resolved


def _safe_workspace_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("Flow reward report path must stay under repository workspace") from exc
    if resolved.is_symlink():
        raise ValueError("Flow reward report path must not be a symlink")
    return resolved


def _clamp(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(1.0, numeric))


def _score_outcome(outcome: Mapping[str, Any]) -> float:
    reward = _clamp(outcome.get("reward") or outcome.get("benefit"))
    evidence = _clamp(outcome.get("evidence") or outcome.get("verification"))
    confidence = _clamp(outcome.get("confidence"))
    success = 1.0 if bool(outcome.get("success")) else 0.0
    regression = _clamp(outcome.get("regression") or outcome.get("failure"))
    cost = _clamp(outcome.get("cost"))
    risk = _clamp(outcome.get("risk"))
    raw = (success * 0.25) + (reward * 0.25) + (evidence * 0.25) + (confidence * 0.10) - (regression * 0.25) - (cost * 0.08) - (risk * 0.07)
    return round(max(0.0, min(1.0, raw)), 4)


def build_flow_reward_report(
    *,
    task: str,
    selected_path_id: str,
    predicted_score: float = 0.0,
    outcomes: Sequence[Mapping[str, Any]],
    source: str = "apex-runtimeos-flow-reward",
) -> Dict[str, Any]:
    """Build a sanitized, read-only Flow reward report."""
    sanitized = []
    for idx, raw in enumerate(outcomes):
        item = {
            "id": _safe_text(raw.get("id") or f"outcome-{idx + 1}", limit=80),
            "summary": _safe_text(raw.get("summary")),
            "success": bool(raw.get("success")),
            "reward": _clamp(raw.get("reward") or raw.get("benefit")),
            "evidence": _clamp(raw.get("evidence") or raw.get("verification")),
            "confidence": _clamp(raw.get("confidence")),
            "regression": _clamp(raw.get("regression") or raw.get("failure")),
            "cost": _clamp(raw.get("cost")),
            "risk": _clamp(raw.get("risk")),
            "side_effects": "observed_only",
        }
        item["outcome_score"] = _score_outcome(item)
        sanitized.append(item)
    if sanitized:
        realized = round(sum(float(item.get("outcome_score") or 0.0) for item in sanitized) / len(sanitized), 4)
    else:
        realized = 0.0
    prediction = _clamp(predicted_score)
    delta = round(realized - prediction, 4)
    if not sanitized:
        status = "BLOCK"
    elif realized >= 0.75 and delta >= -0.15:
        status = "PASS"
    elif realized >= 0.45:
        status = "WATCH"
    else:
        status = "HOLD"
    return {
        "schema": "ApexFlowRewardReport/v1",
        "ts": time.time(),
        "source": _safe_text(source, limit=120),
        "task": _safe_text(task, limit=240),
        "selected_path_id": _safe_text(selected_path_id, limit=80),
        "predicted_score": prediction,
        "realized_score": realized,
        "score_delta": delta,
        "outcome_count": len(sanitized),
        "status": status,
        "outcomes": sanitized[:12],
        "side_effects": "read_only_report",
        "executed_by_this_module": False,
        "routing_feedback_only": True,
    }


def summarize_flow_reward_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "ApexFlowRewardSummary/v1",
        "valid": report.get("schema") == "ApexFlowRewardReport/v1",
        "status": _safe_text(report.get("status"), limit=40),
        "task": _safe_text(report.get("task"), limit=160),
        "selected_path_id": _safe_text(report.get("selected_path_id"), limit=80),
        "predicted_score": float(report.get("predicted_score") or 0.0),
        "realized_score": float(report.get("realized_score") or 0.0),
        "score_delta": float(report.get("score_delta") or 0.0),
        "outcome_count": int(report.get("outcome_count") or 0),
        "executed_by_this_module": bool(report.get("executed_by_this_module")),
        "routing_feedback_only": bool(report.get("routing_feedback_only")),
        "side_effects": "read_only_report",
    }


def write_flow_reward_report(path: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    safe_path = _safe_workspace_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(safe_path), "schema": report.get("schema")}


def default_flow_reward_report_path(task: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in task)[:80] or "flow_reward"
    return _DEFAULT_REPORT_DIR / f"{int(time.time())}_{safe}.json"


def load_latest_flow_reward_report(directory: Path | None = None) -> Dict[str, Any] | None:
    root = _safe_report_dir(directory)
    if not root.exists():
        return None
    candidates = [item for item in root.glob("*.json") if item.is_file() and not item.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: (item.stat().st_mtime, item.name))
    data = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Flow reward report must be a mapping")
    return summarize_flow_reward_report(data)


__all__ = [
    "build_flow_reward_report",
    "default_flow_reward_report_path",
    "load_latest_flow_reward_report",
    "summarize_flow_reward_report",
    "write_flow_reward_report",
]
