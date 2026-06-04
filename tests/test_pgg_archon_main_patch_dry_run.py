from __future__ import annotations

import difflib
import json
import subprocess
from pathlib import Path

from agent.pgg_archon_main_patch_dry_run import evaluate_main_patch_dry_run, main


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, text=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    target = repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text('{"task_id":"old"}\n', encoding="utf-8")
    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "init"], repo)
    return repo


def _bundle(tmp_path: Path, repo: Path, *, bundle_targets: list[str] | None = None) -> Path:
    target = "tests/fixtures/pgg_archon_regressions.jsonl"
    work = tmp_path / "work"
    work.mkdir()
    diff = work / "candidate.diff"
    # Build a real applicable diff without changing the repo.
    original = repo / target
    old = original.read_text(encoding="utf-8")
    new = old + '{"task_id":"new"}\n'
    diff_lines = [
        f"diff --git a/{target} b/{target}\n",
        "index 0000000..1111111 100644\n",
    ]
    unified = list(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{target}",
        tofile=f"b/{target}",
    ))
    diff_lines.extend(unified[2:])
    diff.write_text("".join(diff_lines), encoding="utf-8")
    readiness = work / "readiness.json"
    readiness.write_text(json.dumps({
        "status": "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW",
        "blockers": [],
        "patch_diff": str(diff),
    }), encoding="utf-8")
    bundle = work / "bundle.json"
    bundle.write_text(json.dumps({
        "status": "READY_FOR_HUMAN_MAIN_PATCH_REVIEW",
        "blockers": [],
        "readiness_package": str(readiness),
        "target_files": bundle_targets if bundle_targets is not None else [target],
    }), encoding="utf-8")
    return bundle


def test_main_patch_dry_run_passes_without_mutating_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    before = subprocess.run(["git", "status", "--short"], cwd=str(repo), text=True, capture_output=True, check=True).stdout
    result = evaluate_main_patch_dry_run(review_bundle=bundle, repo_root=repo)
    after = subprocess.run(["git", "status", "--short"], cwd=str(repo), text=True, capture_output=True, check=True).stdout
    assert result.status == "PASS_MAIN_PATCH_DRY_RUN"
    assert result.blockers == []
    assert before == after == ""
    assert (repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl").read_text(encoding="utf-8") == '{"task_id":"old"}\n'


def test_main_patch_dry_run_blocks_target_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bundle = _bundle(tmp_path, repo, bundle_targets=["tests/other.jsonl"])
    result = evaluate_main_patch_dry_run(review_bundle=bundle, repo_root=repo)
    assert result.status == "BLOCKED_MAIN_PATCH_DRY_RUN"
    assert "targets_match_bundle" in result.blockers


def test_main_writes_dry_run_result(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    assert main(["--review-bundle", str(bundle), "--repo-root", str(repo), "--output-dir", str(tmp_path / "out")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS_MAIN_PATCH_DRY_RUN"
    assert Path(printed["result"]).is_file()
