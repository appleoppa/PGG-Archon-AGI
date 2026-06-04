from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.agi_task_benchmark import (
    BenchmarkTask,
    evaluate_predictions,
    load_evolution_queue,
    load_tasks_jsonl,
    run_sample,
    sample_predictions,
    sample_tasks,
    score_prediction,
    write_benchmark_outputs,
)


def test_score_prediction_exact_contains_and_json() -> None:
    exact = BenchmarkTask("t1", "math", "", "42")
    assert score_prediction(exact, " 42 ").passed
    assert not score_prediction(exact, "43").passed

    contains = BenchmarkTask("t2", "boundary", "", "not full agi", scorer="contains_normalized")
    assert score_prediction(contains, "This system is not full AGI.").passed
    assert score_prediction(
        contains,
        "<think>reasoning tokens</think>\nThis system is not full AGI.",
    ).passed

    json_task = BenchmarkTask("t3", "json", "", '{"status":"ok"}', scorer="json_key_value")
    assert score_prediction(json_task, '{"status":"ok"}').passed
    assert score_prediction(json_task, '```json\n{"status": "ok"}\n```').passed
    assert score_prediction(json_task, 'Here is the JSON: {"status": "ok"}').passed
    assert score_prediction(json_task, '<think>x</think>\n{"status":"ok"}').passed
    assert not score_prediction(json_task, "not-json").passed


def test_evaluate_predictions_creates_watch_and_failed_queue(tmp_path: Path) -> None:
    run = evaluate_predictions(sample_tasks(), sample_predictions(perfect=False), run_id="unit-watch")
    assert run.status == "WATCH"
    assert run.total_tasks == 3
    assert run.passed_tasks == 2
    assert run.weighted_score == pytest.approx(2 / 3)
    assert run.failed_task_ids == ["legal-boundary-001"]

    paths = write_benchmark_outputs(run, output_dir=tmp_path)
    assert Path(paths["run"]).is_file()
    assert Path(paths["scores"]).is_file()
    assert Path(paths["evolution_queue"]).is_file()
    queue_lines = Path(paths["evolution_queue"]).read_text(encoding="utf-8").splitlines()
    assert len(queue_lines) == 1
    queue_item = json.loads(queue_lines[0])
    assert queue_item["schema"] == "PGGArchonEvolutionQueueItem/v2"
    assert queue_item["task_id"] == "legal-boundary-001"
    assert queue_item["score_delta"] == 1.0
    assert queue_item["priority"] == "P0"
    assert queue_item["attempt_type"] == "deterministic_benchmark_failure"
    assert queue_item["prompt"] == "State the truthful boundary: this system is not full AGI."
    assert queue_item["weight"] == 1.0
    assert queue_item["tags"] == []
    assert len(queue_item["input_hash"]) == 64
    assert queue_item["promotion_gate"] == "verified_patch_or_skill_required_before_gene_promotion"
    assert queue_item["next_action"] == "analyze_failure_and_add_capability_or_prompt_fix"


def test_evaluate_predictions_perfect_pass(tmp_path: Path) -> None:
    result = run_sample(tmp_path, perfect=True)
    assert result["run"]["status"] == "PASS"
    assert result["run"]["weighted_score"] == 1.0
    queue_path = Path(result["paths"]["evolution_queue"])
    assert queue_path.is_file()
    assert queue_path.read_text(encoding="utf-8") == ""


def test_load_evolution_queue_prioritizes_and_limits(tmp_path: Path) -> None:
    path = tmp_path / "queue.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"task_id": "low", "priority": "P2", "score_delta": 0.2, "created_at": "2026-01-01T00:00:00Z"}),
            json.dumps({"task_id": "high", "priority": "P0", "score_delta": 1.0, "created_at": "2026-01-01T00:00:01Z"}),
            json.dumps({"task_id": "medium", "priority": "P1", "score_delta": 0.8, "created_at": "2026-01-01T00:00:02Z"}),
        ]) + "\n",
        encoding="utf-8",
    )
    assert [item["task_id"] for item in load_evolution_queue(path)] == ["high", "medium", "low"]
    assert [item["task_id"] for item in load_evolution_queue(path, limit=2)] == ["high", "medium"]
    assert load_evolution_queue(tmp_path / "missing.jsonl") == []


def test_load_tasks_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "tasks.jsonl"
    path.write_text(
        json.dumps({
            "task_id": "x",
            "domain": "demo",
            "prompt": "p",
            "expected": "e",
            "scorer": "exact_normalized",
            "tags": ["smoke"],
        }) + "\n",
        encoding="utf-8",
    )
    tasks = load_tasks_jsonl(path)
    assert len(tasks) == 1
    assert tasks[0].task_id == "x"
    assert tasks[0].tags == ("smoke",)


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_predictions([], {})
    with pytest.raises(ValueError):
        evaluate_predictions([BenchmarkTask("bad", "demo", "", "", weight=0)], {})
    with pytest.raises(ValueError):
        score_prediction(BenchmarkTask("bad", "demo", "", "", scorer="unknown"), "")
