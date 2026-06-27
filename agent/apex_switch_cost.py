"""APEX switching-cost guard reports.

The switching-cost layer prevents path thrashing: it compares the currently held
route with a proposed route, estimates transition friction, and recommends
switch/hold without executing either route.  It is read-only and keeps only
sanitized aggregate evidence.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

_MAX_TEXT = 600
_DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "workspace" / "switch_cost"


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = str(value or "").replace("\r", " ").strip()
    lower = text.lower()
    if any(marker in lower for marker in ("api_key", "authorization:", "bearer ", "password", "secret=", "token=")):
        return "[REDACTED]"
    if "/Users/" in text or "\\Users\\" in text:
        return text.replace("/Users/", "[REDACTED_PATH]/").replace("\\Users\\", "[REDACTED_PATH]\\")[:limit]
    return text[:limit]


def _clamp(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(1.0, numeric))


def _safe_workspace_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("Switch-cost report path must stay under repository workspace") from exc
    if resolved.is_symlink():
        raise ValueError("Switch-cost report path must not be a symlink")
    return resolved


def _safe_report_dir(path: Path | None = None) -> Path:
    resolved = (path or _DEFAULT_REPORT_DIR).expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("Switch-cost report directory must stay under repository workspace") from exc
    return resolved


def _feature_set(route: Mapping[str, Any]) -> set[str]:
    raw = route.get("features") or route.get("tools") or route.get("capabilities") or []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return set()
    return {_safe_text(item, limit=80) for item in raw if _safe_text(item, limit=80)}


def _route_score(route: Mapping[str, Any]) -> float:
    reward = _clamp(route.get("reward") or route.get("benefit"))
    evidence = _clamp(route.get("evidence") or route.get("verification"))
    confidence = _clamp(route.get("confidence"))
    risk = _clamp(route.get("risk"))
    cost = _clamp(route.get("cost"))
    uncertainty = _clamp(route.get("uncertainty"))
    raw = (reward * 0.35) + (evidence * 0.25) + (confidence * 0.20) - (risk * 0.25) - (cost * 0.10) - (uncertainty * 0.10)
    return round(max(0.0, min(1.0, raw)), 4)


def _sanitize_route(route: Mapping[str, Any], fallback_id: str) -> Dict[str, Any]:
    item = {
        "id": _safe_text(route.get("id") or fallback_id, limit=80),
        "title": _safe_text(route.get("title"), limit=160),
        "summary": _safe_text(route.get("summary")),
        "risk": _clamp(route.get("risk")),
        "cost": _clamp(route.get("cost")),
        "reward": _clamp(route.get("reward") or route.get("benefit")),
        "evidence": _clamp(route.get("evidence") or route.get("verification")),
        "confidence": _clamp(route.get("confidence")),
        "uncertainty": _clamp(route.get("uncertainty")),
        "features": sorted(_feature_set(route))[:12],
    }
    item["score"] = _route_score(item)
    return item


def _switching_cost(current: Mapping[str, Any], target: Mapping[str, Any], *, explicit_cost: Any = None) -> float:
    if explicit_cost is not None:
        return _clamp(explicit_cost)
    current_features = set(current.get("features") or [])
    target_features = set(target.get("features") or [])
    union = current_features | target_features
    feature_distance = 0.0 if not union else len(current_features ^ target_features) / len(union)
    risk_delta = max(0.0, float(target.get("risk") or 0.0) - float(current.get("risk") or 0.0))
    uncertainty_delta = max(0.0, float(target.get("uncertainty") or 0.0) - float(current.get("uncertainty") or 0.0))
    base = 0.35 * feature_distance + 0.25 * risk_delta + 0.20 * uncertainty_delta + 0.20 * float(target.get("cost") or 0.0)
    return round(max(0.0, min(1.0, base)), 4)


def build_switch_cost_report(
    *,
    task: str,
    current_route: Mapping[str, Any],
    target_route: Mapping[str, Any],
    switching_cost: Any = None,
    hysteresis: float = 0.15,
    source: str = "apex-runtimeos-switch-cost",
) -> Dict[str, Any]:
    """Build a sanitized read-only switching-cost decision report."""
    current = _sanitize_route(current_route, "current")
    target = _sanitize_route(target_route, "target")
    cost = _switching_cost(current, target, explicit_cost=switching_cost)
    threshold = _clamp(hysteresis)
    score_delta = round(float(target.get("score") or 0.0) - float(current.get("score") or 0.0), 4)
    net_gain = round(score_delta - cost, 4)
    if net_gain >= threshold:
        decision = "SWITCH"
        status = "PASS"
    elif net_gain >= 0.0:
        decision = "WATCH"
        status = "WATCH"
    else:
        decision = "HOLD"
        status = "HOLD"
    return {
        "schema": "ApexSwitchCostReport/v1",
        "ts": time.time(),
        "source": _safe_text(source, limit=120),
        "task": _safe_text(task, limit=240),
        "status": status,
        "decision": decision,
        "current_route_id": current.get("id"),
        "target_route_id": target.get("id"),
        "current_score": current.get("score"),
        "target_score": target.get("score"),
        "score_delta": score_delta,
        "switching_cost": cost,
        "hysteresis": threshold,
        "net_gain": net_gain,
        "current_route": current,
        "target_route": target,
        "side_effects": "read_only_report",
        "executed": False,
        "thrash_guard": True,
    }


def summarize_switch_cost_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "ApexSwitchCostSummary/v1",
        "valid": report.get("schema") == "ApexSwitchCostReport/v1",
        "status": _safe_text(report.get("status"), limit=40),
        "decision": _safe_text(report.get("decision"), limit=40),
        "task": _safe_text(report.get("task"), limit=160),
        "current_route_id": _safe_text(report.get("current_route_id"), limit=80),
        "target_route_id": _safe_text(report.get("target_route_id"), limit=80),
        "score_delta": float(report.get("score_delta") or 0.0),
        "switching_cost": float(report.get("switching_cost") or 0.0),
        "net_gain": float(report.get("net_gain") or 0.0),
        "executed": bool(report.get("executed")),
        "thrash_guard": bool(report.get("thrash_guard")),
        "side_effects": "read_only_report",
    }


def write_switch_cost_report(path: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    safe_path = _safe_workspace_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(safe_path), "schema": report.get("schema")}


def default_switch_cost_report_path(task: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in task)[:80] or "switch_cost"
    return _DEFAULT_REPORT_DIR / f"{int(time.time())}_{safe}.json"


def load_latest_switch_cost_report(directory: Path | None = None) -> Dict[str, Any] | None:
    root = _safe_report_dir(directory)
    if not root.exists():
        return None
    candidates = [item for item in root.glob("*.json") if item.is_file() and not item.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: (item.stat().st_mtime, item.name))
    data = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Switch-cost report must be a mapping")
    return summarize_switch_cost_report(data)


__all__ = [
    "build_switch_cost_report",
    "default_switch_cost_report_path",
    "load_latest_switch_cost_report",
    "summarize_switch_cost_report",
    "write_switch_cost_report",
]
