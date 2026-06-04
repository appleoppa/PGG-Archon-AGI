from __future__ import annotations

import json
from pathlib import Path

from agent.agi_task_benchmark import BenchmarkTask, sample_tasks
from agent.pgg_archon_provider_benchmark import (
    ModelProvider,
    _extract_responses_text,
    run_multi_provider_benchmark,
    run_provider_benchmark,
    write_multi_provider_result,
)


def _provider(provider_id: str) -> ModelProvider:
    return ModelProvider(
        provider_id=provider_id,
        model=f"{provider_id}-model",
        api_mode="responses",
        url="https://example.invalid/v1/responses",
        api_key_env="TEST_API_KEY",
    )


def test_extract_responses_text_handles_output_items() -> None:
    data = {
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "hello"}]},
            {"type": "reasoning", "content": []},
        ]
    }
    assert _extract_responses_text(data) == "hello"
    assert _extract_responses_text({"output_text": "fallback"}) == "fallback"


def test_run_provider_benchmark_uses_injected_provider_call(tmp_path: Path) -> None:
    tasks = sample_tasks()

    def fake_call(provider: ModelProvider, task: BenchmarkTask) -> str:
        assert provider.provider_id == "fake-perfect"
        return {
            "math-add-001": "42",
            "json-transform-001": '{"status":"ok"}',
            "legal-boundary-001": "This system is not full AGI.",
        }[task.task_id]

    result = run_provider_benchmark(
        tasks,
        _provider("fake-perfect"),
        output_dir=tmp_path,
        run_id="fake-perfect-run",
        provider_call=fake_call,
    )
    data = result.__dict__
    assert data["schema"] == "PGGArchonProviderBenchmarkResult/v1"
    assert data["status"] in {"PASS", "WATCH"}
    assert data["integrated_result"]["benchmark_run"]["status"] == "PASS"
    assert data["integrated_result"]["benchmark_run"]["weighted_score"] == 1.0
    assert data["integrated_result"]["evolution_queue_count"] == 0
    assert all(item["ok"] for item in data["predictions"])


def test_provider_call_failures_become_benchmark_failures(tmp_path: Path) -> None:
    def failing_call(provider: ModelProvider, task: BenchmarkTask) -> str:
        if task.task_id == "math-add-001":
            return "42"
        raise RuntimeError("provider unavailable")

    result = run_provider_benchmark(
        sample_tasks(),
        _provider("fake-partial"),
        output_dir=tmp_path,
        run_id="fake-partial-run",
        provider_call=failing_call,
    )
    data = result.__dict__
    assert data["status"] == "WATCH"
    assert data["integrated_result"]["benchmark_run"]["passed_tasks"] == 1
    assert data["integrated_result"]["evolution_queue_count"] == 2
    assert sum(1 for item in data["predictions"] if not item["ok"]) == 2


def test_run_multi_provider_benchmark_ranks_by_score_and_writes_files(tmp_path: Path) -> None:
    providers = [_provider("fake-perfect"), _provider("fake-bad")]

    def fake_call(provider: ModelProvider, task: BenchmarkTask) -> str:
        if provider.provider_id == "fake-perfect":
            return {
                "math-add-001": "42",
                "json-transform-001": '{"status":"ok"}',
                "legal-boundary-001": "This system is not full AGI.",
            }[task.task_id]
        return "wrong"

    result = run_multi_provider_benchmark(
        sample_tasks(),
        providers,
        output_dir=tmp_path,
        provider_call=fake_call,
    )
    assert result.schema == "PGGArchonMultiProviderBenchmarkResult/v1"
    assert result.status == "WATCH"
    assert result.ranking[0]["provider_id"] == "fake-perfect"
    assert result.ranking[0]["weighted_score"] == 1.0
    assert result.ranking[1]["provider_id"] == "fake-bad"

    paths = write_multi_provider_result(result, tmp_path)
    assert Path(paths["result"]).is_file()
    assert Path(paths["ranking"]).is_file()
    ranking = json.loads(Path(paths["ranking"]).read_text(encoding="utf-8"))
    assert ranking[0]["provider_id"] == "fake-perfect"
