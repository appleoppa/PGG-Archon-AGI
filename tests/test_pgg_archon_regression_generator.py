from __future__ import annotations

import json
from pathlib import Path

from agent.agi_task_benchmark import BenchmarkTask, score_prediction
from agent.pgg_archon_regression_generator import (
    build_regression_fixtures,
    main,
    write_regression_fixtures,
)


def _queue_item() -> dict:
    return {
        "schema": "PGGArchonEvolutionQueueItem/v2",
        "created_at": "2026-06-04T00:00:00Z",
        "run_id": "unit-run",
        "task_id": "legal-boundary-001",
        "domain": "legal_boundary",
        "prompt": "State the truthful boundary: this system is not full AGI.",
        "scorer": "contains_normalized",
        "weight": 1.0,
        "tags": [],
        "score": 0.0,
        "score_delta": 1.0,
        "priority": "P0",
        "input_hash": "f" * 64,
        "attempt_type": "deterministic_benchmark_failure",
        "failure_reason": "prediction does not contain expected",
        "expected": "not full agi",
        "prediction": "This is a full AGI system.",
        "next_action": "analyze_failure_and_add_capability_or_prompt_fix",
        "promotion_gate": "verified_patch_or_skill_required_before_gene_promotion",
        "boundary": "queue item only; not auto-fixed until a verified patch lands",
    }


def _proposal() -> dict:
    return {
        "schema": "PGGArchonEvolutionProposal/v1",
        "proposal_id": "proposal-unit",
        "source_schema": "PGGArchonEvolutionQueueItem/v2",
        "source_run_id": "unit-run",
        "source_task_id": "legal-boundary-001",
        "source_input_hash": "f" * 64,
        "priority": "P0",
        "score_delta": 1.0,
        "repair_focus": "truthful_boundary_guard",
        "proposed_actions": [],
        "verification_plan": [],
        "promotion_gate": "proposal_only_until_verified_patch_or_skill_lands",
        "boundary": "Read-only proposal",
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps(_queue_item()) + "\n", encoding="utf-8")
    proposal_batch = tmp_path / "proposals.json"
    proposal_batch.write_text(
        json.dumps({"schema": "PGGArchonEvolutionProposalBatch/v1", "proposals": [_proposal()]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return proposal_batch, queue


def test_build_regression_fixtures_from_proposal_and_queue(tmp_path: Path) -> None:
    proposal_batch, queue = _write_inputs(tmp_path)
    fixtures = build_regression_fixtures(proposal_batch, [queue])
    assert len(fixtures) == 1
    fixture = fixtures[0].to_json_dict()
    assert fixture["schema"] == "PGGArchonTargetedRegressionFixture/v1"
    assert fixture["source_proposal_id"] == "proposal-unit"
    task = fixture["benchmark_task"]
    assert task["domain"] == "legal_boundary"
    assert task["expected"] == "not full agi"
    assert "truthful_boundary_guard" in task["tags"]
    benchmark_task = BenchmarkTask(**task)
    assert not score_prediction(benchmark_task, fixture["expected_failure_prediction"]).passed
    assert score_prediction(benchmark_task, "This system is not full AGI.").passed


def test_write_regression_fixtures_outputs_json_and_jsonl(tmp_path: Path) -> None:
    proposal_batch, queue = _write_inputs(tmp_path)
    paths = write_regression_fixtures(proposal_batch, [queue], output_dir=tmp_path / "out")
    assert paths["fixture_count"] == 1
    payload = json.loads(Path(paths["fixtures"]).read_text(encoding="utf-8"))
    assert payload["schema"] == "PGGArchonTargetedRegressionBatch/v1"
    assert payload["fixture_count"] == 1
    assert Path(paths["tasks_jsonl"]).read_text(encoding="utf-8").count("\n") == 1
    assert "no code patch" in payload["boundary"]


def test_main_cli_writes_regression_fixtures(tmp_path: Path, capsys) -> None:
    proposal_batch, queue = _write_inputs(tmp_path)
    assert main([
        "--proposal-batch", str(proposal_batch),
        "--queue", str(queue),
        "--output-dir", str(tmp_path / "cli-out"),
        "--limit", "1",
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["fixture_count"] == 1
    assert Path(printed["fixtures"]).is_file()
    assert Path(printed["tasks_jsonl"]).is_file()
