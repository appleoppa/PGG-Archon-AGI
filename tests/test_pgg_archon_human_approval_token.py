from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.pgg_archon_human_approval_token import (
    REQUIRED_BOUNDARY_ACKS,
    build_human_approval_token,
    main,
    validate_human_approval_token,
    write_human_approval_token,
)


def _dry_run_result(tmp_path: Path) -> Path:
    path = tmp_path / "main_patch_dry_run_result.json"
    path.write_text(json.dumps({
        "schema": "PGGArchonMainPatchDryRunResult/v1",
        "status": "PASS_MAIN_PATCH_DRY_RUN",
        "target_files": ["tests/fixtures/pgg_archon_regressions.jsonl"],
        "blockers": [],
    }), encoding="utf-8")
    return path


def test_build_and_validate_human_approval_token(tmp_path: Path) -> None:
    dry_run = _dry_run_result(tmp_path)
    result = write_human_approval_token(
        dry_run_result=dry_run,
        approver_id="appleoppa",
        repo_head="abc1234",
        approval_statement="I reviewed the dry-run evidence and approve only the gated transaction review.",
        output_dir=tmp_path / "out",
    )
    assert result["status"] == "VALID_HUMAN_APPROVAL_TOKEN"
    token = json.loads(Path(result["token"]).read_text(encoding="utf-8"))
    assert token["schema"] == "PGGArchonHumanApprovalToken/v1"
    assert token["purpose"] == "approved_main_patch_transaction"
    assert token["repo_head"] == "abc1234"
    assert all(ack in token["required_boundary_acknowledgements"] for ack in REQUIRED_BOUNDARY_ACKS)
    validation = validate_human_approval_token(token_path=result["token"], dry_run_result=dry_run, repo_head="abc1234")
    assert validation.status == "VALID_HUMAN_APPROVAL_TOKEN"
    assert validation.blockers == []


def test_token_blocks_when_dry_run_hash_is_tampered(tmp_path: Path) -> None:
    dry_run = _dry_run_result(tmp_path)
    token = build_human_approval_token(
        dry_run_result=dry_run,
        approver_id="appleoppa",
        repo_head="abc1234",
        approval_statement="approve gated transaction review only",
    )
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps(token), encoding="utf-8")
    dry_run.write_text(json.dumps({"status": "PASS_MAIN_PATCH_DRY_RUN", "target_files": ["tests/fixtures/pgg_archon_regressions.jsonl"], "tampered": True}), encoding="utf-8")
    validation = validate_human_approval_token(token_path=token_path, dry_run_result=dry_run, repo_head="abc1234")
    assert validation.status == "BLOCKED_HUMAN_APPROVAL_TOKEN"
    assert "dry_run_sha256_matches" in validation.blockers


def test_token_blocks_repo_head_mismatch_and_missing_ack(tmp_path: Path) -> None:
    dry_run = _dry_run_result(tmp_path)
    token = build_human_approval_token(
        dry_run_result=dry_run,
        approver_id="appleoppa",
        repo_head="abc1234",
        approval_statement="approve gated transaction review only",
    )
    token["required_boundary_acknowledgements"] = ["reviewed_dry_run_result"]
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps(token), encoding="utf-8")
    validation = validate_human_approval_token(token_path=token_path, dry_run_result=dry_run, repo_head="def5678")
    assert validation.status == "BLOCKED_HUMAN_APPROVAL_TOKEN"
    assert "repo_head_matches" in validation.blockers
    assert "boundary_acknowledgements_complete" in validation.blockers
    assert "token_hash_matches" in validation.blockers


def test_token_blocks_when_expired(tmp_path: Path) -> None:
    dry_run = _dry_run_result(tmp_path)
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result = write_human_approval_token(
        dry_run_result=dry_run,
        approver_id="appleoppa",
        repo_head="abc1234",
        approval_statement="approve gated transaction review only",
        output_dir=tmp_path / "out",
        expires_at=expired,
    )
    validation = validate_human_approval_token(token_path=result["token"], dry_run_result=dry_run, repo_head="abc1234")
    assert validation.status == "BLOCKED_HUMAN_APPROVAL_TOKEN"
    assert "not_expired" in validation.blockers


def test_cli_create_and_validate(tmp_path: Path, capsys) -> None:
    dry_run = _dry_run_result(tmp_path)
    assert main([
        "create",
        "--dry-run-result", str(dry_run),
        "--approver-id", "appleoppa",
        "--repo-head", "abc1234",
        "--approval-statement", "approve gated transaction review only",
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["status"] == "VALID_HUMAN_APPROVAL_TOKEN"
    assert main([
        "validate",
        "--token", created["token"],
        "--dry-run-result", str(dry_run),
        "--repo-head", "abc1234",
        "--output-dir", str(tmp_path / "validate"),
    ]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated["status"] == "VALID_HUMAN_APPROVAL_TOKEN"
    assert Path(validated["validation"]).is_file()
