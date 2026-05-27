"""APEX Co-Scientist structured debate reports.

This module is intentionally read-only: it structures model review outputs into a
sanitized report for later evidence/gene-candidate review. It does not call LLMs,
execute code, mutate memory, or promote skills.
"""
from __future__ import annotations

import hashlib
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


def _safe_report_dir(path: Path | None = None) -> Path:
    resolved = (path or _DEFAULT_REPORT_DIR).expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("co-scientist report directory must stay under repository workspace") from exc
    return resolved


def validate_debate_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a compact validation report for a Co-Scientist debate report."""
    errors: list[str] = []
    if report.get("schema") != "ApexCoScientistDebateReport/v1":
        errors.append("schema")
    reviewers = report.get("reviewers")
    if not isinstance(reviewers, list):
        errors.append("reviewers")
    if not isinstance(report.get("reviewer_count"), int):
        errors.append("reviewer_count")
    if str(report.get("side_effects") or "") != "read_only_report":
        errors.append("side_effects")
    return {
        "schema": "ApexCoScientistDebateValidation/v1",
        "valid": not errors,
        "errors": errors,
        "side_effects": "read_only_report",
    }


def summarize_debate_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Reduce a debate report to autonomy-safe aggregate fields."""
    validation = validate_debate_report(report)
    return {
        "schema": "ApexCoScientistDebateSummary/v1",
        "valid": bool(validation.get("valid")),
        "status": _safe_text(report.get("status"), limit=40),
        "topic": _safe_text(report.get("topic"), limit=160),
        "reviewer_count": int(report.get("reviewer_count") or 0) if isinstance(report.get("reviewer_count"), int) else 0,
        "ok_count": int(report.get("ok_count") or 0) if isinstance(report.get("ok_count"), int) else 0,
        "decision": _safe_text(report.get("decision"), limit=80),
        "promotion_required": bool(report.get("promotion_required")),
        "applied_to_memory_or_skill": bool(report.get("applied_to_memory_or_skill")),
        "validation_errors": validation.get("errors", []),
        "side_effects": "read_only_report",
    }


def build_gene_candidate_from_debate(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a read-only gene candidate from a validated debate report.

    The candidate is deliberately non-promoting: it can feed future lifecycle
    gates, but it never writes the gene library or durable memory/skills.
    """
    summary = summarize_debate_report(report)
    candidate_id = hashlib.sha256(
        json.dumps(
            {
                "topic": summary.get("topic"),
                "decision": summary.get("decision"),
                "reviewer_count": summary.get("reviewer_count"),
                "ok_count": summary.get("ok_count"),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    eligible = (
        bool(summary.get("valid"))
        and summary.get("status") == "PASS"
        and int(summary.get("reviewer_count") or 0) >= 2
        and int(summary.get("ok_count") or 0) >= 2
        and summary.get("decision") in {"execute", "accept", "pass"}
        and bool(summary.get("promotion_required"))
        and not bool(summary.get("applied_to_memory_or_skill"))
    )
    blockers = []
    if not summary.get("valid"):
        blockers.append("invalid_report")
    if summary.get("status") != "PASS":
        blockers.append("debate_not_pass")
    if int(summary.get("reviewer_count") or 0) < 2:
        blockers.append("insufficient_reviewers")
    if int(summary.get("ok_count") or 0) < 2:
        blockers.append("insufficient_ok_reviews")
    if summary.get("decision") not in {"execute", "accept", "pass"}:
        blockers.append("decision_not_promotable")
    if bool(summary.get("applied_to_memory_or_skill")):
        blockers.append("already_applied_elsewhere")
    return {
        "schema": "ApexCoScientistGeneCandidate/v1",
        "candidate_id": candidate_id,
        "source_schema": str(report.get("schema") or ""),
        "source": "co_scientist_debate_report",
        "topic": summary.get("topic", ""),
        "status": "READY" if eligible else "HOLD",
        "eligible": eligible,
        "blockers": blockers,
        "reviewer_count": summary.get("reviewer_count", 0),
        "ok_count": summary.get("ok_count", 0),
        "decision": summary.get("decision", ""),
        "evidence_level": "multi_model_debate" if eligible else "insufficient",
        "promotion_required": True,
        "gene_library_written": False,
        "applied_to_memory_or_skill": False,
        "side_effects": "read_only_candidate",
    }


def write_gene_candidate(path: Path, candidate: Mapping[str, Any]) -> Dict[str, Any]:
    """Persist a read-only gene candidate under workspace."""
    safe_path = _safe_workspace_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(json.dumps(dict(candidate), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(safe_path), "schema": candidate.get("schema")}


def default_gene_candidate_path(topic: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in topic)[:80] or "gene_candidate"
    return Path(__file__).resolve().parents[1] / "workspace" / "co_scientist_gene_candidates" / f"{int(time.time())}_{safe}.json"


def _safe_workspace_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo_workspace = (Path(__file__).resolve().parents[1] / "workspace").resolve()
    try:
        resolved.relative_to(repo_workspace)
    except ValueError as exc:
        raise ValueError("co-scientist candidate path must stay under repository workspace") from exc
    if resolved.is_symlink():
        raise ValueError("co-scientist candidate path must not be a symlink")
    return resolved


def summarize_gene_candidate(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    """Reduce a gene candidate to autonomy-safe aggregate fields."""
    return {
        "schema": "ApexCoScientistGeneCandidateSummary/v1",
        "status": _safe_text(candidate.get("status"), limit=40),
        "eligible": bool(candidate.get("eligible")),
        "candidate_id": _safe_text(candidate.get("candidate_id"), limit=32),
        "topic": _safe_text(candidate.get("topic"), limit=160),
        "decision": _safe_text(candidate.get("decision"), limit=80),
        "reviewer_count": int(candidate.get("reviewer_count") or 0) if isinstance(candidate.get("reviewer_count"), int) else 0,
        "evidence_level": _safe_text(candidate.get("evidence_level"), limit=80),
        "promotion_required": bool(candidate.get("promotion_required")),
        "gene_library_written": bool(candidate.get("gene_library_written")),
        "side_effects": "read_only_candidate",
    }


def load_latest_gene_candidate(directory: Path | None = None) -> Dict[str, Any] | None:
    """Load and summarize the newest Co-Scientist gene candidate under workspace."""
    root = _safe_report_dir(directory or (Path(__file__).resolve().parents[1] / "workspace" / "co_scientist_gene_candidates"))
    if not root.exists():
        return None
    candidates = [item for item in root.glob("*.json") if item.is_file() and not item.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: (item.stat().st_mtime, item.name))
    data = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("co-scientist gene candidate must be a mapping")
    if data.get("schema") != "ApexCoScientistGeneCandidate/v1":
        raise ValueError("co-scientist gene candidate schema mismatch")
    return summarize_gene_candidate(data)


def load_latest_debate_report(directory: Path | None = None) -> Dict[str, Any] | None:
    """Load and summarize the newest Co-Scientist report under workspace."""
    root = _safe_report_dir(directory)
    if not root.exists():
        return None
    candidates = [item for item in root.glob("*.json") if item.is_file() and not item.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: (item.stat().st_mtime, item.name))
    data = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("co-scientist report must be a mapping")
    return summarize_debate_report(data)


__all__ = [
    "build_debate_report",
    "build_gene_candidate_from_debate",
    "default_debate_report_path",
    "default_gene_candidate_path",
    "load_latest_debate_report",
    "load_latest_gene_candidate",
    "summarize_debate_report",
    "summarize_gene_candidate",
    "validate_debate_report",
    "write_debate_report",
    "write_gene_candidate",
]
