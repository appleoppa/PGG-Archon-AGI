from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_provider_health_gate import (
    build_provider_health_gate_report,
    classify_provider_result,
    load_multi_provider_result,
    write_provider_health_gate_report,
)


def _provider_result(provider_id: str, score: float, passed: int, total: int, *, transport_failures: int = 0):
    predictions = []
    for i in range(total):
        failed_transport = i < transport_failures
        predictions.append(
            {
                "task_id": f"t{i}",
                "ok": not failed_transport,
                "http_status": 502 if failed_transport else 200,
                "error": "HTTP 502" if failed_transport else None,
                "prediction": "" if failed_transport else "ok",
            }
        )
    return {
        "provider": {"provider_id": provider_id, "model": f"{provider_id}-model"},
        "predictions": predictions,
        "integrated_result": {
            "benchmark_run": {
                "weighted_score": score,
                "passed_tasks": passed,
                "total_tasks": total,
            },
            "evolution_queue_count": total - passed,
        },
    }


def test_classify_provider_result_separates_transport_and_capability() -> None:
    down = classify_provider_result(_provider_result("gpt", 0.0, 0, 3, transport_failures=3))
    assert down.health == "DOWN"
    assert down.route == "BLOCK_PROVIDER_USE_FALLBACK"
    assert down.transport_failures == 3
    assert down.capability_failures == 0

    degraded = classify_provider_result(_provider_result("claude", 0.666667, 2, 3))
    assert degraded.health == "DEGRADED_CAPABILITY"
    assert degraded.route == "FALLBACK_OR_SPECIALIZED"
    assert degraded.transport_failures == 0
    assert degraded.capability_failures == 1

    healthy = classify_provider_result(_provider_result("deepseek", 1.0, 3, 3))
    assert healthy.health == "HEALTHY"
    assert healthy.route == "PRIMARY_CANDIDATE"


def test_build_provider_health_gate_report_ranks_and_routes() -> None:
    report = build_provider_health_gate_report(
        {
            "results": [
                _provider_result("gpt", 0.0, 0, 3, transport_failures=3),
                _provider_result("claude", 0.666667, 2, 3),
                _provider_result("deepseek", 1.0, 3, 3),
                _provider_result("minimax", 1.0, 3, 3),
            ]
        }
    )
    assert report.schema == "PGGArchonProviderHealthGate/v1"
    assert report.status == "PASS"
    assert report.primary_provider == "deepseek"
    assert report.fallback_providers == ["minimax", "claude"]
    assert report.blocked_providers == ["gpt"]
    assert report.decisions[0]["provider_id"] == "deepseek"
    assert report.decisions[1]["provider_id"] == "minimax"


def test_write_and_load_provider_health_gate_report(tmp_path: Path) -> None:
    multi = {
        "results": [
            _provider_result("deepseek", 1.0, 3, 3),
        ]
    }
    multi_path = tmp_path / "multi.json"
    multi_path.write_text(json.dumps(multi), encoding="utf-8")
    loaded = load_multi_provider_result(multi_path)
    report = build_provider_health_gate_report(loaded)
    paths = write_provider_health_gate_report(report, tmp_path)
    assert Path(paths["health_gate"]).is_file()
    data = json.loads(Path(paths["health_gate"]).read_text(encoding="utf-8"))
    assert data["primary_provider"] == "deepseek"
