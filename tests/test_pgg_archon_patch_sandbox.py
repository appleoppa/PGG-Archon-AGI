from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_patch_sandbox import (
    evaluate_patch_candidate,
    main,
    write_patch_sandbox_results,
)


def _candidate() -> dict:
    return {
        "schema": "PGGArchonPatchCandidate/v1",
        "candidate_id": "patch-candidate-unit",
        "source_fixture_id": "regression-unit",
        "source_input_hash": "f" * 64,
        "repair_focus": "truthful_boundary_guard",
        "candidate_type": "read_only_patch_plan",
        "target_surfaces": ["target.py", "tests"],
        "proposed_patch_steps": [],
        "verification_commands": ["python -m py_compile target.py"],
        "risk_level": "LOW",
        "promotion_gate": "candidate_plan_only_until_patch_is_applied_and_tests_manifest_readback_pass",
        "boundary": "Read-only patch candidate plan.",
    }


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    return root


def _batch(tmp_path: Path) -> Path:
    path = tmp_path / "patch_candidates.json"
    path.write_text(json.dumps({"schema": "PGGArchonPatchCandidateBatch/v1", "candidates": [_candidate()]}, ensure_ascii=False), encoding="utf-8")
    return path


def test_evaluate_patch_candidate_checks_surfaces_and_commands(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = evaluate_patch_candidate(_candidate(), repo_root=root)
    data = result.to_json_dict()
    assert data["schema"] == "PGGArchonPatchSandboxResult/v1"
    assert data["status"] == "PASS_READY_FOR_ISOLATED_PATCH"
    assert data["patch_applicable"] is True
    assert all(item["exists"] for item in data["target_surface_checks"])
    assert data["verification_results"][0]["exit"] == 0
    assert "no patch applied" in data["boundary"]


def test_write_patch_sandbox_results_outputs_batch(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    candidate_batch = _batch(tmp_path)
    paths = write_patch_sandbox_results(candidate_batch, repo_root=root, output_dir=tmp_path / "out")
    assert paths["result_count"] == 1
    assert paths["pass_count"] == 1
    payload = json.loads(Path(paths["batch"]).read_text(encoding="utf-8"))
    assert payload["schema"] == "PGGArchonPatchSandboxBatch/v1"
    assert payload["pass_count"] == 1
    assert Path(paths["jsonl"]).read_text(encoding="utf-8").count("\n") == 1


def test_main_cli_writes_sandbox_results(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    candidate_batch = _batch(tmp_path)
    assert main([
        "--candidates", str(candidate_batch),
        "--repo-root", str(root),
        "--output-dir", str(tmp_path / "cli-out"),
        "--limit", "1",
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["result_count"] == 1
    assert printed["pass_count"] == 1
    assert Path(printed["batch"]).is_file()
