"""PGG Archon read-only evidence loop surface.

Aggregates the lightweight learning-loop evidence that already exists around
PGG Archon: case/event ledger signals, failure samples, three-question task
retrospectives, low-risk autonomy candidates, multi-model review ledger, and
real capability metrics.  This module is intentionally read-only; it does not
call models, execute case workflows, write genes, or claim AGI completion.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.apex_failure_sample_library import build_failure_sample_library_status, load_failure_samples
from agent.apex_low_risk_autonomy_candidates import generate_autonomy_candidates
from agent.apex_multi_model_evidence_ledger import build_multi_model_evidence_ledger
from agent.apex_real_capability_metrics import build_real_capability_metrics_summary
from agent.apex_task_retrospective import DEFAULT_RETROSPECTIVE_DIR, build_task_retrospective_status


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _load_jsonl(path: str | Path) -> tuple[dict[str, Any], ...]:
    p = Path(path)
    if not p.exists():
        return ()
    out: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                out.append(parsed)
    return tuple(out)


def _signal(ok: bool, source: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "reason": reason,
        "source_schema": source.get("schema"),
    }


def build_pgg_archon_evidence_loop_surface(
    snapshot: Mapping[str, Any] | None = None,
    *,
    case_events_path: str | Path | None = None,
    failure_library_dir: str | Path | None = None,
    task_retrospective_dir: str | Path | None = None,
    review_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build a read-only machine-checkable learning-loop surface.

    ``snapshot`` may provide already-redacted aggregate lists for tests or
    callers: ``events``, ``failure_samples``, ``task_retrospectives``,
    ``autonomy_candidates`` and ``multi_model_ledger``.
    """
    data = snapshot if isinstance(snapshot, Mapping) else {}

    events = tuple(_as_sequence(data.get("events")))
    if case_events_path is not None:
        events += _load_jsonl(case_events_path)
    elif "events" not in data:
        try:
            from agent.pgg_case_experience_bridge import DEFAULT_EVENTS_DIR

            events += _load_jsonl(DEFAULT_EVENTS_DIR / "case_events.jsonl")
        except Exception:
            events += ()

    failure_status = dict(data.get("failure_sample_library") or {}) if isinstance(data.get("failure_sample_library"), Mapping) else {}
    if not failure_status:
        if failure_library_dir is not None:
            failure_status = build_failure_sample_library_status(library_dir=failure_library_dir)
        else:
            failure_status = build_failure_sample_library_status()

    failure_samples = tuple(_as_sequence(data.get("failure_samples")))
    if "failure_samples" not in data:
        try:
            if failure_library_dir is not None:
                failure_samples += tuple(load_failure_samples(library_dir=failure_library_dir))
            else:
                failure_samples += tuple(load_failure_samples())
        except Exception:
            failure_samples += ()

    retrospective_status = dict(data.get("task_retrospective_status") or {}) if isinstance(data.get("task_retrospective_status"), Mapping) else {}
    if not retrospective_status:
        if task_retrospective_dir is not None:
            retrospective_status = build_task_retrospective_status(library_dir=task_retrospective_dir)
        else:
            retrospective_status = build_task_retrospective_status()

    retrospectives = tuple(_as_sequence(data.get("task_retrospectives")))
    if "task_retrospectives" not in data:
        try:
            base = Path(task_retrospective_dir) if task_retrospective_dir is not None else DEFAULT_RETROSPECTIVE_DIR
            retrospectives += _load_jsonl(base / "retrospectives.jsonl")
        except Exception:
            retrospectives += ()

    multi_model_ledger = dict(data.get("multi_model_evidence_ledger") or {}) if isinstance(data.get("multi_model_evidence_ledger"), Mapping) else {}
    if not multi_model_ledger:
        kwargs = {"review_dir": review_dir} if review_dir is not None else {}
        multi_model_ledger = build_multi_model_evidence_ledger(**kwargs)

    autonomy_candidates = tuple(_as_sequence(data.get("autonomy_candidates")))
    autonomy_candidate_report = dict(data.get("autonomy_candidate_report") or {}) if isinstance(data.get("autonomy_candidate_report"), Mapping) else {}
    if not autonomy_candidate_report:
        autonomy_candidate_report = generate_autonomy_candidates({
            "failure_samples": failure_samples,
            "real_capability_metrics": {"status": "WATCH"},
        })
        autonomy_candidates += tuple(_as_sequence(autonomy_candidate_report.get("candidates")))

    capability_metrics = dict(data.get("real_capability_metrics") or {}) if isinstance(data.get("real_capability_metrics"), Mapping) else {}
    if not capability_metrics:
        capability_metrics = build_real_capability_metrics_summary({
            "events": events,
            "failure_samples": failure_samples,
            "task_retrospectives": retrospectives,
            "autonomy_candidates": autonomy_candidates,
            "multi_model_ledger": tuple(_as_sequence(multi_model_ledger.get("entries"))),
        })

    signals = {
        "event_ledger_observed": _signal(len(events) > 0, {}, f"event_count={len(events)}"),
        "failure_learning_observed": _signal(_status(failure_status.get("status")) == "PASS", failure_status, f"failure_status={_status(failure_status.get('status'))}"),
        "task_retrospective_observed": _signal(_status(retrospective_status.get("status")) == "PASS", retrospective_status, f"retrospective_status={_status(retrospective_status.get('status'))}"),
        "multi_model_evidence_observed": _signal(_status(multi_model_ledger.get("status")) == "PASS" and int(multi_model_ledger.get("provider_count") or 0) > 0, multi_model_ledger, f"provider_count={int(multi_model_ledger.get('provider_count') or 0)}"),
        "real_capability_metrics_observed": _signal(_status(capability_metrics.get("status")) in {"PASS", "WATCH"} and int(capability_metrics.get("known_metric_count") or 0) > 0, capability_metrics, f"known_metric_count={int(capability_metrics.get('known_metric_count') or 0)}"),
    }
    ok_count = sum(1 for item in signals.values() if item["ok"])
    score = round(100 * ok_count / len(signals), 1)
    missing = [name for name, item in signals.items() if not item["ok"]]
    status = "PASS" if not missing else ("WATCH" if ok_count else "UNKNOWN")

    return {
        "schema": "PGGArchonEvidenceLoopSurface/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "score": score,
        "signals": signals,
        "missing": missing,
        "summary": {
            "event_count": len(events),
            "failure_sample_count": failure_status.get("sample_count"),
            "task_retrospective_count": retrospective_status.get("retrospective_count"),
            "multi_model_provider_count": multi_model_ledger.get("provider_count"),
            "real_capability_known_metric_count": capability_metrics.get("known_metric_count"),
        },
        "failure_sample_library": failure_status,
        "task_retrospective_status": retrospective_status,
        "multi_model_evidence_ledger": multi_model_ledger,
        "real_capability_metrics": capability_metrics,
        "autonomy_candidate_report": autonomy_candidate_report,
        "side_effects": "read_only_evidence_loop_surface",
        "external_calls_made": False,
        "agi_completion_claim": False,
    }


__all__ = ["build_pgg_archon_evidence_loop_surface"]
