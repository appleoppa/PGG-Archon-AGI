from __future__ import annotations

import difflib
import json
import subprocess
from pathlib import Path

from agent.pgg_archon_approved_main_patch_transaction import (
    prepare_approved_main_patch_transaction,
    main,
)
from agent.pgg_archon_human_approval_token import write_human_approval_token


def _run(cmd: list[str], cwd: Path) -> str:
    return subprocess.run(cmd, cwd=str(cwd), check=True, text=True, capture_output=True).stdout


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


def _dry_run_and_token(tmp_path: Path, repo: Path) -> tuple[Path, Path]:
    target = "tests/fixtures/pgg_archon_regressions.jsonl"
    old = (repo / target).read_text(encoding="utf-8")
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
    work = tmp_path / "work"
    work.mkdir()
    diff = work / "candidate.diff"
    diff.write_text("".join(diff_lines), encoding="utf-8")
    dry = work / "main_patch_dry_run_result.json"
    dry.write_text(json.dumps({
        "schema": "PGGArchonMainPatchDryRunResult/v1",
        "status": "PASS_MAIN_PATCH_DRY_RUN",
        "patch_diff": str(diff),
        "target_files": [target],
        "blockers": [],
    }), encoding="utf-8")
    head = _run(["git", "rev-parse", "--short", "HEAD"], repo).strip()
    token_result = write_human_approval_token(
        dry_run_result=dry,
        approver_id="appleoppa",
        repo_head=head,
        approval_statement="approve future gated transaction package only",
        output_dir=work / "token",
    )
    return dry, Path(token_result["token"])


def test_prepare_transaction_package_without_mutating_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    dry, token = _dry_run_and_token(tmp_path, repo)
    before_status = _run(["git", "status", "--short"], repo)
    before_content = (repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl").read_text(encoding="utf-8")
    result = prepare_approved_main_patch_transaction(
        token_path=token,
        dry_run_result=dry,
        repo_root=repo,
        output_dir=tmp_path / "out",
    )
    after_status = _run(["git", "status", "--short"], repo)
    after_content = (repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl").read_text(encoding="utf-8")
    assert result.status == "READY_APPROVED_MAIN_PATCH_TRANSACTION_PACKAGE"
    assert result.blockers == []
    assert result.transaction_package and Path(result.transaction_package).is_file()
    assert result.rollback_package and Path(result.rollback_package).is_file()
    assert before_status == after_status == ""
    assert before_content == after_content == '{"task_id":"old"}\n'
    tx = json.loads(Path(result.transaction_package).read_text(encoding="utf-8"))
    assert tx["status"] == "READY_FOR_APPROVED_MAIN_PATCH_TRANSACTION"
    assert tx["forbidden_by_this_gate"]
    rollback = json.loads(Path(result.rollback_package).read_text(encoding="utf-8"))
    assert rollback["schema"] == "PGGArchonMainPatchRollbackPackage/v1"
    assert rollback["target_files"][0]["exists"] is True


def test_prepare_transaction_blocks_invalid_token(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    dry, token = _dry_run_and_token(tmp_path, repo)
    data = json.loads(token.read_text(encoding="utf-8"))
    data["repo_head"] = "wronghead"
    token.write_text(json.dumps(data), encoding="utf-8")
    result = prepare_approved_main_patch_transaction(
        token_path=token,
        dry_run_result=dry,
        repo_root=repo,
        output_dir=tmp_path / "out",
    )
    assert result.status == "BLOCKED_APPROVED_MAIN_PATCH_TRANSACTION"
    assert "token_valid" in result.blockers
    assert result.transaction_package is None
    assert result.rollback_package is None


def test_cli_writes_transaction_result(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    dry, token = _dry_run_and_token(tmp_path, repo)
    assert main([
        "--token", str(token),
        "--dry-run-result", str(dry),
        "--repo-root", str(repo),
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "READY_APPROVED_MAIN_PATCH_TRANSACTION_PACKAGE"
    assert Path(printed["result"]).is_file()
    assert Path(printed["transaction_package"]).is_file()
    assert Path(printed["rollback_package"]).is_file()
