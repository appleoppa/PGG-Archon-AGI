import json
from pathlib import Path

from agent.route_chain_stage_retry_replay import (
    build_stage_retry_replay_ledger,
    build_stage_retry_replay_ledger_from_path,
    classify_stage_for_retry,
)


def _stage(**overrides):
    base = {
        "task_id": "rceg_test",
        "stage": "GPT主脑统筹",
        "provider": "gpt55_5yuantoken",
        "model_id": "gpt-5.5",
        "input_hash": "in-hash",
        "output_hash": "out-hash",
        "response_id": "resp-1",
        "verdict": "pass",
        "reason_code": "real_model_call",
        "record_hash": "stage-hash",
    }
    base.update(overrides)
    return base


def test_classify_complete_stage_needs_no_replay():
    decision = classify_stage_for_retry(_stage())
    assert decision.status == "COMPLETE"
    assert decision.action == "none"
    assert decision.max_retries == 0


def test_classify_timeout_as_same_provider_retry():
    decision = classify_stage_for_retry(
        _stage(response_id=None, output_hash=None, verdict="fail", reason_code="model_call_failed", error="TimeoutError: timed out")
    )
    assert decision.status == "REPLAY_REQUIRED"
    assert decision.action == "retry_same_provider"
    assert decision.retry_after_seconds == 30
    assert "transient_network_or_rate_limit" in decision.reason_codes


def test_classify_404_as_fallback_replay():
    decision = classify_stage_for_retry(
        _stage(provider="minimax-cn", response_id=None, output_hash=None, verdict="fail", reason_code="model_call_failed", error="HTTP Error 404: endpoint not found")
    )
    assert decision.action == "replay_with_fallback_provider"
    assert decision.requires_fallback is True
    assert "provider_or_endpoint_unavailable" in decision.reason_codes


def test_build_ledger_counts_replay_required_and_writes_file(tmp_path):
    record = {
        "task_id": "rceg_test",
        "record_hash": "record-hash",
        "stage_outputs": [
            _stage(stage="GPT主脑统筹"),
            _stage(stage="旁证压缩", provider="minimax-cn", response_id=None, output_hash=None, verdict="fail", reason_code="model_call_failed", error="404 endpoint"),
            _stage(stage="GPT主脑收束", response_id=None, output_hash=None, verdict="fail", reason_code="model_call_failed", error="TimeoutError"),
        ],
    }
    ledger = build_stage_retry_replay_ledger(record, write_ledger=True, ledger_dir=tmp_path)
    assert ledger["schema"] == "RouteChainStageRetryReplayLedger/v1"
    assert ledger["stage_count"] == 3
    assert ledger["complete_stage_count"] == 1
    assert ledger["replay_required_count"] == 2
    assert ledger["retryable_count"] == 2
    assert ledger["final_recommendation"] == "replay_required"
    assert Path(ledger["ledger_path"]).exists()
    assert ledger["agi_completion_claim"] is False


def test_build_ledger_from_path_preserves_source_path(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"task_id": "rceg_path", "record_hash": "rh", "stage_outputs": [_stage()]}, ensure_ascii=False), encoding="utf-8")
    ledger = build_stage_retry_replay_ledger_from_path(evidence, write_ledger=False)
    assert ledger["source_evidence_path"] == str(evidence)
    assert ledger["final_recommendation"] == "no_replay_needed"
