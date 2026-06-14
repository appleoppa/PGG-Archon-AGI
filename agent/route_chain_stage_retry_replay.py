"""Stage-level retry/replay ledger for route-chain evidence records.

This module reduces Net/Run residual risk by turning failed or incomplete
route-chain stages into a deterministic retry/replay plan. It is deliberately
non-executing: it does not call models, patch files, or mutate evidence records.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_LEDGER_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/stage-retry-replay")
RETRYABLE_ERROR_TOKENS = (
    "timeout",
    "timed out",
    "temporarily unavailable",
    "429",
    "503",
    "502",
    "connection",
    "urlerror",
    "remote end closed",
)
FALLBACK_ERROR_TOKENS = (
    "404",
    "not found",
    "endpoint",
    "missing env",
    "unauthorized",
    "401",
    "403",
)


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _stage_error_text(stage: Mapping[str, Any]) -> str:
    parts = [stage.get("error"), stage.get("reason_code"), stage.get("fallback_reason"), stage.get("provider"), stage.get("model_id")]
    return " ".join(str(p or "") for p in parts).lower()


@dataclass(frozen=True)
class StageReplayDecision:
    stage: str
    provider: str | None
    model_id: str | None
    status: str
    action: str
    reason_codes: tuple[str, ...]
    retry_after_seconds: int | None
    max_retries: int
    requires_fallback: bool
    replay_input_hash: str | None
    original_record_hash: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "provider": self.provider,
            "model_id": self.model_id,
            "status": self.status,
            "action": self.action,
            "reason_codes": list(self.reason_codes),
            "retry_after_seconds": self.retry_after_seconds,
            "max_retries": self.max_retries,
            "requires_fallback": self.requires_fallback,
            "replay_input_hash": self.replay_input_hash,
            "original_record_hash": self.original_record_hash,
        }


def classify_stage_for_retry(stage: Mapping[str, Any]) -> StageReplayDecision:
    text = _stage_error_text(stage)
    reasons: list[str] = []
    has_response = bool(stage.get("response_id"))
    has_output_hash = bool(stage.get("output_hash"))
    verdict = str(stage.get("verdict") or "").lower()
    reason_code = str(stage.get("reason_code") or "")
    if has_response and has_output_hash and reason_code != "model_call_failed":
        return StageReplayDecision(
            stage=str(stage.get("stage") or ""),
            provider=stage.get("provider"),
            model_id=stage.get("model_id"),
            status="COMPLETE",
            action="none",
            reason_codes=(),
            retry_after_seconds=None,
            max_retries=0,
            requires_fallback=False,
            replay_input_hash=stage.get("input_hash"),
            original_record_hash=stage.get("record_hash"),
        )
    if not has_response:
        reasons.append("missing_response_id")
    if not has_output_hash:
        reasons.append("missing_output_hash")
    if reason_code == "model_call_failed" or verdict == "fail":
        reasons.append("model_call_failed")
    if any(token in text for token in RETRYABLE_ERROR_TOKENS):
        reasons.append("transient_network_or_rate_limit")
    if any(token in text for token in FALLBACK_ERROR_TOKENS):
        reasons.append("provider_or_endpoint_unavailable")
    requires_fallback = "provider_or_endpoint_unavailable" in reasons
    if "transient_network_or_rate_limit" in reasons and not requires_fallback:
        action = "retry_same_provider"
        retry_after = 30
        max_retries = 2
    elif requires_fallback:
        action = "replay_with_fallback_provider"
        retry_after = 5
        max_retries = 1
    else:
        action = "manual_replay_review"
        retry_after = None
        max_retries = 0
    return StageReplayDecision(
        stage=str(stage.get("stage") or ""),
        provider=stage.get("provider"),
        model_id=stage.get("model_id"),
        status="REPLAY_REQUIRED",
        action=action,
        reason_codes=tuple(dict.fromkeys(reasons)),
        retry_after_seconds=retry_after,
        max_retries=max_retries,
        requires_fallback=requires_fallback,
        replay_input_hash=stage.get("input_hash"),
        original_record_hash=stage.get("record_hash"),
    )


def build_stage_retry_replay_ledger(record: Mapping[str, Any], *, write_ledger: bool = False, ledger_dir: str | Path = DEFAULT_LEDGER_DIR) -> dict[str, Any]:
    stages = [_as_mapping(s) for s in record.get("stage_outputs") or []]
    decisions = [classify_stage_for_retry(stage).to_dict() for stage in stages]
    replay_required = [d for d in decisions if d["status"] == "REPLAY_REQUIRED"]
    retryable = [d for d in replay_required if d["action"] in {"retry_same_provider", "replay_with_fallback_provider"}]
    ledger = {
        "schema": "RouteChainStageRetryReplayLedger/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_task_id": record.get("task_id"),
        "source_record_hash": record.get("record_hash"),
        "stage_count": len(stages),
        "complete_stage_count": len([d for d in decisions if d["status"] == "COMPLETE"]),
        "replay_required_count": len(replay_required),
        "retryable_count": len(retryable),
        "decisions": decisions,
        "final_recommendation": "replay_required" if replay_required else "no_replay_needed",
        "side_effects": "ledger_write" if write_ledger else "read_only_plan",
        "agi_completion_claim": False,
    }
    ledger["ledger_hash"] = _sha256_obj(ledger)
    if write_ledger:
        out_dir = Path(ledger_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        task_id = str(record.get("task_id") or "unknown").replace("/", "_")[:80]
        out = out_dir / f"{int(time.time())}_{task_id}_retry_replay.json"
        out.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        ledger["ledger_path"] = str(out)
    return ledger


def build_stage_retry_replay_ledger_from_path(evidence_path: str | Path, *, write_ledger: bool = True, ledger_dir: str | Path = DEFAULT_LEDGER_DIR) -> dict[str, Any]:
    record = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    ledger = build_stage_retry_replay_ledger(record, write_ledger=write_ledger, ledger_dir=ledger_dir)
    ledger["source_evidence_path"] = str(evidence_path)
    return ledger


__all__ = [
    "build_stage_retry_replay_ledger",
    "build_stage_retry_replay_ledger_from_path",
    "classify_stage_for_retry",
]
