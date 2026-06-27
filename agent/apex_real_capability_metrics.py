"""Read-only real capability metrics for APEX/PGG service quality.

The metrics in this module intentionally report UNKNOWN/WATCH when evidence is
missing.  They do not infer service quality from file existence, generated
reports, reference-only skills, or claimed model calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


METRIC_IDS: tuple[str, ...] = (
    "factual_grounding",
    "evidence_chain",
    "legal_basis_verification",
    "tool_verified_execution",
    "delivery_completion",
    "failure_learning",
    "task_retrospective",
    "low_risk_autonomy",
    "multi_model_evidence",
)


@dataclass(frozen=True)
class CapabilityMetric:
    metric_id: str
    label: str
    status: str
    score: float | None
    evidence_count: int
    missing: tuple[str, ...]
    evidence_hashes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "label": self.label,
            "status": self.status,
            "score": self.score,
            "evidence_count": self.evidence_count,
            "missing": list(self.missing),
            "evidence_hashes": list(self.evidence_hashes),
        }


_LABELS = {
    "factual_grounding": "事实查证与来源绑定",
    "evidence_chain": "证据链完整性",
    "legal_basis_verification": "法律依据核验",
    "tool_verified_execution": "工具执行与验收",
    "delivery_completion": "交付闭环",
    "failure_learning": "失败样本学习",
    "task_retrospective": "真实任务三问复盘",
    "low_risk_autonomy": "低风险自治候选",
    "multi_model_evidence": "多模型互补证据",
}


_EVENT_KEYWORDS = {
    "factual_grounding": ("source", "citation", "fact_checked", "verified_fact"),
    "evidence_chain": ("evidence_hash", "evidence_bundle", "artifact_hash"),
    "legal_basis_verification": ("legal_basis", "statute", "case_citation", "law_checked"),
    "tool_verified_execution": ("tool_call", "pytest", "verification", "test_result"),
    "delivery_completion": ("delivered", "acceptance", "remote_head", "commit_sha"),
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _event_text(event: Mapping[str, Any]) -> str:
    safe_parts: list[str] = []
    for key, value in event.items():
        if key.lower() in {"raw_content", "content", "prompt", "response", "secret", "api_key"}:
            continue
        safe_parts.append(f"{key}={value}")
    return " ".join(safe_parts).lower()


def _hashes(items: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    out: list[str] = []
    for item in items:
        h = item.get("evidence_hash") or item.get("artifact_hash") or item.get("hash")
        if isinstance(h, str) and h and h not in out:
            out.append(h)
    return tuple(out[:12])


def _metric_from_events(metric_id: str, events: Sequence[Any], required: tuple[str, ...]) -> CapabilityMetric:
    mapped = [_as_mapping(e) for e in events]
    hits = [e for e in mapped if any(token in _event_text(e) for token in required)]
    if not events:
        return CapabilityMetric(metric_id, _LABELS[metric_id], "UNKNOWN", None, 0, ("no_safe_aggregate_events",))
    if not hits:
        return CapabilityMetric(metric_id, _LABELS[metric_id], "WATCH", 0.0, 0, (f"missing_{metric_id}_evidence",))
    score = round(min(100.0, 100.0 * len(hits) / max(1, len(events))), 1)
    status = "PASS" if score >= 60 else "WATCH"
    return CapabilityMetric(metric_id, _LABELS[metric_id], status, score, len(hits), (), _hashes(hits))


def _metric_from_library(metric_id: str, records: Sequence[Any], required_keys: tuple[str, ...]) -> CapabilityMetric:
    mapped = [_as_mapping(r) for r in records]
    complete = [r for r in mapped if all(r.get(k) for k in required_keys)]
    if not records:
        return CapabilityMetric(metric_id, _LABELS[metric_id], "UNKNOWN", None, 0, (f"no_{metric_id}_records",))
    if not complete:
        return CapabilityMetric(metric_id, _LABELS[metric_id], "WATCH", 0.0, 0, (f"incomplete_{metric_id}_schema",))
    score = round(100.0 * len(complete) / len(records), 1)
    return CapabilityMetric(metric_id, _LABELS[metric_id], "PASS" if score >= 60 else "WATCH", score, len(complete), (), _hashes(complete))


def build_real_capability_metrics_summary(snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a read-only summary from safe aggregate evidence.

    Expected optional inputs are already-redacted aggregate structures:
    ``events``, ``failure_samples``, ``task_retrospectives``,
    ``autonomy_candidates`` and ``multi_model_ledger``. Missing data returns
    UNKNOWN/WATCH instead of fabricated scores.
    """
    data = _as_mapping(snapshot or {})
    events = _as_sequence(data.get("events"))
    failure_samples = _as_sequence(data.get("failure_samples"))
    retrospectives = _as_sequence(data.get("task_retrospectives"))
    autonomy_candidates = _as_sequence(data.get("autonomy_candidates"))
    multi_model_ledger = _as_sequence(data.get("multi_model_ledger"))

    metrics: list[CapabilityMetric] = []
    for metric_id, required in _EVENT_KEYWORDS.items():
        metrics.append(_metric_from_events(metric_id, events, required))
    metrics.append(_metric_from_library("failure_learning", failure_samples, ("error_type", "next_intercept_method", "evidence_hash")))
    metrics.append(_metric_from_library("task_retrospective", retrospectives, ("what_happened", "why", "next_change", "evidence_hash")))
    metrics.append(_metric_from_library("low_risk_autonomy", autonomy_candidates, ("candidate_type", "status", "review_required", "evidence_hash")))
    metrics.append(_metric_from_library("multi_model_evidence", multi_model_ledger, ("provider", "model", "status", "decision", "evidence_hash")))

    known = [m for m in metrics if m.score is not None]
    overall_score = None if not known else round(sum(m.score for m in known if m.score is not None) / len(known), 1)
    if not known:
        status = "UNKNOWN"
    elif any(m.status == "WATCH" for m in metrics) or len(known) < len(metrics):
        status = "WATCH"
    else:
        status = "PASS"
    return {
        "schema": "ApexRealCapabilityMetrics/v1",
        "status": status,
        "overall_score": overall_score,
        "metric_count": len(metrics),
        "known_metric_count": len(known),
        "unknown_metric_count": len(metrics) - len(known),
        "metrics": {m.metric_id: m.to_dict() for m in metrics},
        "side_effects": "read_only_summary",
        "claims": {"agi_complete": False, "autonomous_promotion_enabled": False},
    }


__all__ = ["METRIC_IDS", "CapabilityMetric", "build_real_capability_metrics_summary"]
