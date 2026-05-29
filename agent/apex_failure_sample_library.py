"""Append-only redacted failure sample library for APEX/PGG.

Samples are stored without raw sensitive content.  The library is intentionally
simple and local: JSONL append-only records under workspace/failure_samples.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DEFAULT_LIBRARY_DIR = Path("workspace/failure_samples")

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
)

_REQUIRED_FIELDS = (
    "error_type",
    "trigger_scenario",
    "root_cause",
    "correct_action",
    "auto_detection_rule",
    "next_intercept_method",
    "evidence_hash",
)


@dataclass(frozen=True)
class FailureSample:
    error_type: str
    trigger_scenario: str
    root_cause: str
    correct_action: str
    auto_detection_rule: str
    next_intercept_method: str
    evidence_hash: str
    redacted_excerpt: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ApexFailureSample/v1",
            "created_at": self.created_at or datetime.now(timezone.utc).isoformat(),
            "error_type": self.error_type,
            "trigger_scenario": self.trigger_scenario,
            "root_cause": self.root_cause,
            "correct_action": self.correct_action,
            "auto_detection_rule": self.auto_detection_rule,
            "next_intercept_method": self.next_intercept_method,
            "evidence_hash": self.evidence_hash,
            "redacted_excerpt": self.redacted_excerpt,
            "sensitive_content_stored": False,
        }


def redact_sensitive_text(text: str) -> str:
    redacted = str(text or "")
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted[:1200]


def evidence_hash_from_text(text: str) -> str:
    redacted = redact_sensitive_text(text)
    return hashlib.sha256(redacted.encode("utf-8")).hexdigest()


def _normalise(value: Any) -> str:
    return redact_sensitive_text(str(value or "")).strip()


def build_detection_rule(error_type: str, trigger_scenario: str, root_cause: str = "") -> str:
    text = f"{error_type} {trigger_scenario} {root_cause}".lower()
    if any(token in text for token in ("飞书", "feishu", "格式", "format", "表格", "markdown", "混乱")):
        return "detect_malformed_feishu_or_markdown_structure: require ordered headings, stable bullets, and non-empty fields before delivery"
    if "agi" in text:
        return "detect_forbidden_agi_completion_claim: force agi_completion_claim=false unless external ground truth and human authorization exist"
    if any(token in text for token in ("报告当完成", "file exists", "文件存在", "完成")):
        return "detect_completion_claim_without_acceptance_evidence: block when only a report/file exists without tests/readback/delivery proof"
    if any(token in text for token in ("reference_only", "trusted skill", "技能")):
        return "detect_reference_only_skill_trust: block trusted-skill promotion when source is reference_only or unverified"
    if any(token in text for token in ("gpt", "claude", "多模型", "model call", "外呼")):
        return "detect_unverified_model_call_claim: require provider/model/status/evidence_hash ledger before claiming multi-model review"
    return "detect_repeated_failure_pattern: match error_type + trigger_scenario and require next_intercept_method before delivery"


def build_failure_sample(payload: Mapping[str, Any]) -> FailureSample:
    error_type = _normalise(payload.get("error_type")) or "unknown_error"
    trigger = _normalise(payload.get("trigger_scenario")) or "unknown_trigger"
    root = _normalise(payload.get("root_cause")) or "root_cause_unknown"
    correct = _normalise(payload.get("correct_action")) or "verify_with_evidence_before_claiming_completion"
    rule = _normalise(payload.get("auto_detection_rule")) or build_detection_rule(error_type, trigger, root)
    intercept = _normalise(payload.get("next_intercept_method")) or f"pre_delivery_guard:{rule.split(':', 1)[0]}"
    raw_evidence = str(payload.get("evidence") or payload.get("raw_content") or " ".join([error_type, trigger, root, correct, rule, intercept]))
    evidence_hash = _normalise(payload.get("evidence_hash")) or evidence_hash_from_text(raw_evidence)
    excerpt = redact_sensitive_text(str(payload.get("redacted_excerpt") or payload.get("raw_content") or raw_evidence))
    return FailureSample(error_type, trigger, root, correct, rule, intercept, evidence_hash, excerpt)


def append_failure_sample(payload: Mapping[str, Any], *, library_dir: str | Path = DEFAULT_LIBRARY_DIR, filename: str = "samples.jsonl") -> dict[str, Any]:
    sample = build_failure_sample(payload)
    record = sample.to_dict()
    missing = [field for field in _REQUIRED_FIELDS if not record.get(field)]
    if missing:
        raise ValueError(f"failure sample missing required fields: {missing}")
    target_dir = Path(library_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    before = target.stat().st_size if target.exists() else 0
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    after = target.stat().st_size
    return {
        "schema": "ApexFailureSampleAppendResult/v1",
        "status": "APPENDED",
        "path": str(target),
        "bytes_before": before,
        "bytes_after": after,
        "append_only": after > before,
        "record": record,
    }


def load_failure_samples(*, library_dir: str | Path = DEFAULT_LIBRARY_DIR, filename: str = "samples.jsonl") -> list[dict[str, Any]]:
    target = Path(library_dir) / filename
    if not target.exists():
        return []
    out: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                out.append(parsed)
    return out


def build_failure_sample_library_status(*, library_dir: str | Path = DEFAULT_LIBRARY_DIR, filename: str = "samples.jsonl") -> dict[str, Any]:
    samples = load_failure_samples(library_dir=library_dir, filename=filename)
    complete = [s for s in samples if all(s.get(field) for field in _REQUIRED_FIELDS) and s.get("sensitive_content_stored") is False]
    status = "UNKNOWN" if not samples else ("PASS" if len(complete) == len(samples) else "WATCH")
    return {
        "schema": "ApexFailureSampleLibraryStatus/v1",
        "status": status,
        "sample_count": len(samples),
        "complete_sample_count": len(complete),
        "library_dir": str(library_dir),
        "append_only": True,
        "stores_raw_sensitive_content": False,
        "side_effects": "read_only_status",
    }


__all__ = [
    "FailureSample",
    "append_failure_sample",
    "build_detection_rule",
    "build_failure_sample",
    "build_failure_sample_library_status",
    "evidence_hash_from_text",
    "load_failure_samples",
    "redact_sensitive_text",
]
