"""APEX Co-Scientist structured debate reports.

This module is intentionally read-only: it structures model review outputs into a
sanitized report for later evidence/gene-candidate review. It does not call LLMs,
execute code, mutate memory, or promote skills.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

_ALLOWED_ROLES = {"reasoning", "coding", "review", "red_team", "synthesis"}
_MAX_TEXT = 600
_DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "workspace" / "co_scientist"


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = str(value or "").replace("\r", " ").strip()
    lower = text.lower()
    if any(marker in lower for marker in ("api_key", "authorization:", "bearer ", "password", "secret=")):
        return "[REDACTED]"
    if "/Users/" in text or "\\Users\\" in text:
        return text.replace("/Users/", "[REDACTED_PATH]/").replace("\\Users\\", "[REDACTED_PATH]\\")[:limit]
    return text[:limit]


def build_debate_report(
    *,
    topic: str,
    reviewers: Sequence[Mapping[str, Any]],
    synthesis: str = "",
    decision: str = "hold",
    source: str = "apex-runtimeos-co-scientist",
) -> Dict[str, Any]:
    """Build a sanitized, schema-stable Co-Scientist debate report."""
    sanitized_reviewers = []
    for raw in reviewers:
        role = str(raw.get("role") or "review")
        if role not in _ALLOWED_ROLES:
            role = "review"
        sanitized_reviewers.append({
            "provider": _safe_text(raw.get("provider"), limit=80),
            "model": _safe_text(raw.get("model"), limit=80),
            "role": role,
            "status": _safe_text(raw.get("status") or "unknown", limit=40),
            "claim": _safe_text(raw.get("claim")),
            "risk": _safe_text(raw.get("risk")),
            "verification": _safe_text(raw.get("verification")),
        })
    ok_count = sum(1 for item in sanitized_reviewers if item.get("status") == "ok")
    report = {
        "schema": "ApexCoScientistDebateReport/v1",
        "ts": time.time(),
        "source": _safe_text(source, limit=120),
        "topic": _safe_text(topic, limit=240),
        "reviewer_count": len(sanitized_reviewers),
        "ok_count": ok_count,
        "decision": _safe_text(decision, limit=80),
        "synthesis": _safe_text(synthesis),
        "reviewers": sanitized_reviewers,
        "side_effects": "read_only_report",
        "promotion_required": True,
        "applied_to_memory_or_skill": False,
    }
    report["status"] = "PASS" if ok_count >= 2 and decision in {"execute", "accept", "pass"} else "WATCH"
    return report


def write_debate_report(path: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    """Persist a debate report under a caller-selected workspace path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(path), "schema": report.get("schema")}


def default_debate_report_path(topic: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in topic)[:80] or "debate"
    return _DEFAULT_REPORT_DIR / f"{int(time.time())}_{safe}.json"


__all__ = ["build_debate_report", "default_debate_report_path", "write_debate_report"]
