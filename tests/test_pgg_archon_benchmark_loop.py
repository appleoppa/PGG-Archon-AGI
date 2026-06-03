from __future__ import annotations

from pathlib import Path

from agent.agi_task_benchmark import sample_predictions, sample_tasks
from agent.pgg_archon_benchmark_loop import run_integrated_benchmark


def test_integrated_benchmark_loop_watch_uses_existing_pgg_surfaces(tmp_path: Path) -> None:
    result = run_integrated_benchmark(
        sample_tasks(),
        sample_predictions(perfect=False),
        output_dir=tmp_path,
        run_id="integrated-watch",
    )
    data = result.to_json_dict()
    assert data["schema"] == "PGGArchonIntegratedBenchmarkLoop/v1"
    assert data["status"] == "WATCH"
    assert data["benchmark_run"]["status"] == "WATCH"
    assert data["evolution_queue_count"] == 1
    assert data["pgg_status"]["schema"] == "HermesPGGStatusRust/v1"
    assert data["pgg_ecc"]["schema"] == "HermesPGGEccRust/v1"
    assert data["delta_gate"]["schema"] == "PGGDeltaGateBenchmarkSignal/v1"
    assert Path(data["output_paths"]["integrated"]).is_file()


def test_integrated_benchmark_loop_pass_has_empty_queue(tmp_path: Path) -> None:
    result = run_integrated_benchmark(
        sample_tasks(),
        sample_predictions(perfect=True),
        output_dir=tmp_path,
        run_id="integrated-pass",
    )
    data = result.to_json_dict()
    assert data["benchmark_run"]["status"] == "PASS"
    assert data["benchmark_run"]["weighted_score"] == 1.0
    assert data["evolution_queue_count"] == 0
    assert Path(data["output_paths"]["integrated"]).is_file()


def test_integrated_benchmark_loop_can_call_apex_eval(tmp_path: Path) -> None:
    result = run_integrated_benchmark(
        sample_tasks(),
        sample_predictions(perfect=True),
        output_dir=tmp_path,
        run_id="integrated-apex",
        workspace_for_apex="/Users/appleoppa/.hermes/workspace/进化/agi_fast_path_20260603",
    )
    data = result.to_json_dict()
    assert data["apex_delta_e"] is not None
    assert "apex_delta_e" in data["apex_delta_e"] or data["apex_delta_e"].get("status") == "WATCH"
