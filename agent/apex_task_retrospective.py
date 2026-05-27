"""Task retrospective evidence schema for real-task feeding loops."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from agent.apex_failure_sample_library import redact_sensitive_text

DEFAULT_RETROSPECTIVE_DIR = Path("workspace/task_retrospectives")


@dataclass(frozen=True)
class TaskRetrospective:
    task_id: str
    what_happened: str
    why: str
    next_change: str
    evidence_hash: str
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ApexTaskRetrospective/v1",
            "created_at": self.created_at or datetime.now(timezone.utc).isoformat(),
            "task_id": self.task_id,
            "what_happened": self.what_happened,
            "why": self.why,
            "next_change": self.next_change,
            "evidence_hash": self.evidence_hash,
            "questions": ["what_happened", "why", "next_change"],
            "sensitive_content_stored": False,
        }


def _hash(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def build_task_retrospective(payload: Mapping[str, Any]) -> TaskRetrospective:
    task_id = redact_sensitive_text(str(payload.get("task_id") or "unknown_task"))[:160]
    what = redact_sensitive_text(str(payload.get("what_happened") or payload.get("what") or ""))
    why = redact_sensitive_text(str(payload.get("why") or ""))
    next_change = redact_sensitive_text(str(payload.get("next_change") or payload.get("next") or ""))
    if not all((what, why, next_change)):
        raise ValueError("task retrospective requires what_happened, why, and next_change")
    evidence_hash = str(payload.get("evidence_hash") or _hash([task_id, what, why, next_change]))
    return TaskRetrospective(task_id, what, why, next_change, evidence_hash)


def append_task_retrospective(payload: Mapping[str, Any], *, library_dir: str | Path = DEFAULT_RETROSPECTIVE_DIR, filename: str = "retrospectives.jsonl") -> dict[str, Any]:
    record = build_task_retrospective(payload).to_dict()
    target_dir = Path(library_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    before = target.stat().st_size if target.exists() else 0
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "schema": "ApexTaskRetrospectiveAppendResult/v1",
        "status": "APPENDED",
        "path": str(target),
        "bytes_before": before,
        "bytes_after": target.stat().st_size,
        "record": record,
    }


def build_task_retrospective_status(*, library_dir: str | Path = DEFAULT_RETROSPECTIVE_DIR, filename: str = "retrospectives.jsonl") -> dict[str, Any]:
    target = Path(library_dir) / filename
    if not target.exists():
        return {"schema": "ApexTaskRetrospectiveStatus/v1", "status": "UNKNOWN", "retrospective_count": 0, "side_effects": "read_only_status"}
    records = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                records.append(json.loads(line))
    complete = [r for r in records if all(r.get(k) for k in ("what_happened", "why", "next_change", "evidence_hash"))]
    return {
        "schema": "ApexTaskRetrospectiveStatus/v1",
        "status": "PASS" if records and len(complete) == len(records) else "WATCH",
        "retrospective_count": len(records),
        "complete_count": len(complete),
        "side_effects": "read_only_status",
    }


__all__ = ["TaskRetrospective", "append_task_retrospective", "build_task_retrospective", "build_task_retrospective_status"]
