from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent.pgg_archon_patch_apply_sandbox import main, write_patch_apply_sandbox_result


def _run(cmd, cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _run(["git", "init"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / "agent").mkdir()
    (root / "tests").mkdir()
    (root / "tests" / "fixtures").mkdir()
    (root / "tests" / "fixtures" / "pgg_archon_regressions.jsonl").write_text(
        json.dumps({"task_id": "regression-existing", "domain": "demo", "prompt": "old", "expected": "old"}) + "\n",
        encoding="utf-8",
    )
    (root / "agent" / "agi_task_benchmark.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "agent" / "pgg_archon_regression_generator.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests" / "test_agi_task_benchmark.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (root / "tests" / "test_pgg_archon_regression_generator.py").write_text("def test_ok2():\n    assert True\n", encoding="utf-8")
    _run(["git", "add", "."], root)
    _run(["git", "commit", "-m", "init"], root)
    return root


def _candidate_batch(tmp_path: Path) -> Path:
    path = tmp_path / "patch_candidates.json"
    candidate = {
        "schema": "PGGArchonPatchCandidate/v1",
        "candidate_id": "patch-candidate-unit",
        "verification_commands": ["python -m py_compile agent/agi_task_benchmark.py agent/pgg_archon_regression_generator.py", "git diff --check"],
    }
    path.write_text(json.dumps({"schema": "PGGArchonPatchCandidateBatch/v1", "candidates": [candidate]}, ensure_ascii=False), encoding="utf-8")
    return path


def _tasks(tmp_path: Path) -> Path:
    path = tmp_path / "tasks.jsonl"
    path.write_text(json.dumps({"task_id": "regression-demo", "domain": "demo", "prompt": "p", "expected": "e"}) + "\n", encoding="utf-8")
    return path


def test_write_patch_apply_sandbox_result_uses_temp_worktree(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = write_patch_apply_sandbox_result(
        _candidate_batch(tmp_path),
        repo_root=repo,
        output_dir=tmp_path / "out",
        regression_tasks_jsonl=_tasks(tmp_path),
        keep_worktree=True,
    )
    assert result["status"] == "PASS_PATCH_SANDBOX"
    payload = json.loads(Path(result["result"]).read_text(encoding="utf-8"))
    assert payload["changed_files"] == ["tests/fixtures/pgg_archon_regressions.jsonl"]
    assert Path(payload["diff_path"]).read_text(encoding="utf-8").strip()
    repo_fixture = repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl"
    assert "regression-existing" in repo_fixture.read_text(encoding="utf-8")
    assert "regression-demo" not in repo_fixture.read_text(encoding="utf-8")
    worktree_fixture = Path(payload["worktree_path"]) / "tests" / "fixtures" / "pgg_archon_regressions.jsonl"
    fixture_text = worktree_fixture.read_text(encoding="utf-8")
    assert "regression-existing" in fixture_text
    assert "regression-demo" in fixture_text
    _run(["git", "worktree", "remove", "--force", payload["worktree_path"]], repo)


def test_main_cli_writes_patch_apply_result(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    assert main([
        "--candidates", str(_candidate_batch(tmp_path)),
        "--repo-root", str(repo),
        "--output-dir", str(tmp_path / "cli-out"),
        "--regression-tasks-jsonl", str(_tasks(tmp_path)),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS_PATCH_SANDBOX"
    payload = json.loads(Path(printed["result"]).read_text(encoding="utf-8"))
    _run(["git", "worktree", "remove", "--force", payload["worktree_path"]], repo)
