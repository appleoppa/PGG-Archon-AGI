from __future__ import annotations

import difflib
import json
import subprocess
from pathlib import Path

from agent.pgg_archon_approved_main_patch_transaction import prepare_approved_main_patch_transaction
from agent.pgg_archon_human_approval_token import write_human_approval_token
from agent.pgg_archon_regression_rollback_verifier import main, verify_regression_and_rollback


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


def _transaction_package(tmp_path: Path, repo: Path) -> Path:
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
    tx_result = prepare_approved_main_patch_transaction(
        token_path=token_result["token"],
        dry_run_result=dry,
        repo_root=repo,
        output_dir=work / "tx",
    )
    assert tx_result.transaction_package
    return Path(tx_result.transaction_package)


def test_verify_regression_and_rollback_without_mutating_main_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tx = _transaction_package(tmp_path, repo)
    before_status = _run(["git", "status", "--short"], repo)
    before_content = (repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl").read_text(encoding="utf-8")
    result = verify_regression_and_rollback(
        transaction_package=tx,
        repo_root=repo,
        verification_commands=(["git", "diff", "--check"],),
    )
    after_status = _run(["git", "status", "--short"], repo)
    after_content = (repo / "tests" / "fixtures" / "pgg_archon_regressions.jsonl").read_text(encoding="utf-8")
    assert result.status == "PASS_REGRESSION_ROLLBACK_VERIFICATION"
    assert result.blockers == []
    assert result.apply_result["exit"] == 0
    assert result.rollback_result["exit"] == 0
    assert result.checks["target_hashes_changed_after_apply"] is True
    assert result.checks["target_hashes_restored_after_rollback"] is True
    assert before_status == after_status == ""
    assert before_content == after_content == '{"task_id":"old"}\n'


def test_verify_blocks_bad_transaction_status(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    tx = _transaction_package(tmp_path, repo)
    data = json.loads(tx.read_text(encoding="utf-8"))
    data["status"] = "NOT_READY"
    tx.write_text(json.dumps(data), encoding="utf-8")
    result = verify_regression_and_rollback(transaction_package=tx, repo_root=repo)
    assert result.status == "BLOCKED_REGRESSION_ROLLBACK_VERIFICATION"
    assert "transaction_ready" in result.blockers


def test_cli_writes_verification_result(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    tx = _transaction_package(tmp_path, repo)
    assert main([
        "--transaction-package", str(tx),
        "--repo-root", str(repo),
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS_REGRESSION_ROLLBACK_VERIFICATION"
    assert Path(printed["result"]).is_file()
