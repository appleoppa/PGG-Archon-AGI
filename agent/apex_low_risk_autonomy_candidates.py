"""Read-only low-risk autonomy candidate generator for APEX/PGG."""
from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence


def _safe_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_autonomy_candidates(snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = snapshot or {}
    failures_value = data.get("failure_samples")
    failures = failures_value if isinstance(failures_value, Sequence) and not isinstance(failures_value, (str, bytes, bytearray)) else []
    metrics_value = data.get("real_capability_metrics")
    metrics = metrics_value if isinstance(metrics_value, Mapping) else {}
    candidates: list[dict[str, Any]] = []
    if failures:
        candidates.append({
            "candidate_type": "memory_candidate",
            "status": "REVIEW_REQUIRED",
            "review_required": True,
            "title": "失败样本拦截记忆候选",
            "reason": "failure_sample_library_has_records",
            "evidence_hash": _safe_hash(str(len(failures)) + "failure_samples"),
            "writes_formal_memory": False,
        })
    metric_status = str(metrics.get("status") or "UNKNOWN")
    if metric_status in {"WATCH", "UNKNOWN"}:
        candidates.append({
            "candidate_type": "skill_draft",
            "status": "REVIEW_REQUIRED",
            "review_required": True,
            "title": "真实能力指标补齐技能草案",
            "reason": f"real_capability_metrics_status={metric_status}",
            "evidence_hash": _safe_hash(metric_status + "real_capability_metrics"),
            "writes_formal_skill": False,
        })
    return {
        "schema": "ApexLowRiskAutonomyCandidates/v1",
        "status": "PASS" if candidates else "UNKNOWN",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "side_effects": "read_only_candidates",
        "formal_skill_written": False,
        "formal_memory_written": False,
    }


__all__ = ["generate_autonomy_candidates"]
