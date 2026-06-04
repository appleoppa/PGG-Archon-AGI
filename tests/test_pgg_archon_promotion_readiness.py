from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_promotion_readiness import build_promotion_readiness_package, main


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _evidence(tmp_path: Path, *, diff_exists: bool = True) -> dict[str, Path]:
    queue = tmp_path / "sample.evolution_queue.jsonl"
    queue.write_text('{"task_id":"x"}\n', encoding="utf-8")
    diff = tmp_path / "candidate.diff"
    if diff_exists:
        diff.write_text("diff --git a/x b/x\n", encoding="utf-8")
    tasks = tmp_path / "targeted_regression_tasks.jsonl"
    tasks.write_text('{"task_id":"x"}\n', encoding="utf-8")
    return {
        "source_queue": queue,
        "proposal_batch": _write(tmp_path / "evolution_proposals.json", {"proposal_count": 1, "proposals": [{}]}),
        "regression_fixtures": _write(tmp_path / "targeted_regression_fixtures.json", {"fixture_count": 1, "fixtures": [{}]}),
        "regression_tasks_jsonl": tasks,
        "patch_candidates": _write(tmp_path / "patch_candidates.json", {"candidate_count": 1, "candidates": [{}]}),
        "sandbox_results": _write(tmp_path / "patch_sandbox_results.json", {"pass_count": 1, "results": [{}]}),
        "patch_apply_result": _write(tmp_path / "patch_apply_sandbox_result.json", {"status": "PASS_PATCH_SANDBOX", "diff_path": str(diff)}),
    }


def test_build_promotion_readiness_package_ready(tmp_path: Path) -> None:
    pkg = build_promotion_readiness_package(**_evidence(tmp_path))
    assert pkg.status == "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW"
    assert pkg.blockers == []
    assert pkg.readiness_checks["patch_apply_passed"] is True


def test_build_promotion_readiness_package_blocks_missing_diff(tmp_path: Path) -> None:
    pkg = build_promotion_readiness_package(**_evidence(tmp_path, diff_exists=False))
    assert pkg.status == "BLOCKED_READINESS_PACKAGE"
    assert "patch_diff_exists" in pkg.blockers


def test_main_writes_readiness_package(tmp_path: Path, capsys) -> None:
    ev = _evidence(tmp_path)
    assert main([
        "--source-queue", str(ev["source_queue"]),
        "--proposal-batch", str(ev["proposal_batch"]),
        "--regression-fixtures", str(ev["regression_fixtures"]),
        "--regression-tasks-jsonl", str(ev["regression_tasks_jsonl"]),
        "--patch-candidates", str(ev["patch_candidates"]),
        "--sandbox-results", str(ev["sandbox_results"]),
        "--patch-apply-result", str(ev["patch_apply_result"]),
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW"
    assert Path(printed["package"]).is_file()
