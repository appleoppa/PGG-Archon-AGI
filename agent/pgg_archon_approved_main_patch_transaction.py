"""PGG Archon approved main patch transaction gate.

Boundary: prepares and validates a future approved main-worktree patch
transaction from a valid human approval token and V3-P0 dry-run evidence. The
default path is prepare-only: it never applies the patch, commits, mutates
GeneDB, calls providers, or claims AGI completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from agent.pgg_archon_human_approval_token import validate_human_approval_token

TRANSACTION_SCHEMA = "PGGArchonApprovedMainPatchTransaction/v1"
ROLLBACK_SCHEMA = "PGGArchonMainPatchRollbackPackage/v1"


@dataclass(frozen=True)
class ApprovedMainPatchTransactionResult:
    schema: str
    generated_at: str
    status: str
    token_path: str
    dry_run_result: str
    patch_diff: str
    repo_root: str
    repo_head: str | None
    target_files: list[str]
    checks: dict[str, bool]
    blockers: list[str]
    transaction_package: str | None
    rollback_package: str | None
    git_apply_check: dict[str, Any]
    git_status_before: str
    git_status_after: str
    next_action: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {p}")
    return data


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).expanduser().read_bytes()).hexdigest()


def _run(cmd: list[str], *, cwd: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        return {"cmd": cmd, "exit": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": cmd, "exit": None, "error": repr(exc)}


def _git_status(repo_root: Path) -> str:
    return str(_run(["git", "status", "--short"], cwd=repo_root, timeout=30).get("stdout") or "")


def _git_head(repo_root: Path) -> str | None:
    result = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, timeout=30)
    if result.get("exit") == 0:
        return str(result.get("stdout") or "").strip()
    return None


def _diff_targets(diff_text: str) -> list[str]:
    targets: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                targets.append(parts[3][2:])
    return targets


def _build_rollback_package(*, repo_root: Path, patch_diff: Path, target_files: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for target in target_files:
        target_path = repo_root / target
        if target_path.is_file():
            files.append({
                "path": target,
                "exists": True,
                "sha256_before": hashlib.sha256(target_path.read_bytes()).hexdigest(),
                "size_before": target_path.stat().st_size,
            })
        else:
            files.append({"path": target, "exists": False, "sha256_before": None, "size_before": None})
    return {
        "schema": ROLLBACK_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repo_head_before": _git_head(repo_root),
        "patch_diff": str(patch_diff),
        "patch_diff_sha256": _sha256_file(patch_diff) if patch_diff.is_file() else None,
        "target_files": files,
        "rollback_commands": [
            "git apply -R <candidate.diff>",
            "python -m pytest <transaction regression tests>",
            "git diff --check",
        ],
        "boundary": "Rollback package only; generated before any approved transaction mutation.",
    }


def prepare_approved_main_patch_transaction(
    *,
    token_path: str | Path,
    repo_root: str | Path,
    output_dir: str | Path,
    dry_run_result: str | Path | None = None,
) -> ApprovedMainPatchTransactionResult:
    repo = Path(repo_root).expanduser()
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    token = _load_json(token_path)
    dry_path = Path(dry_run_result or token.get("dry_run_result") or "").expanduser()
    dry = _load_json(dry_path) if dry_path.is_file() else {}
    validation = validate_human_approval_token(token_path=token_path, dry_run_result=dry_path, repo_head=_git_head(repo))
    patch_path = Path(str(dry.get("patch_diff") or "")).expanduser()
    patch_text = patch_path.read_text(encoding="utf-8") if patch_path.is_file() else ""
    target_files = _diff_targets(patch_text)
    status_before = _git_status(repo)
    apply_check = _run(["git", "apply", "--check", str(patch_path)], cwd=repo, timeout=60) if patch_path.is_file() else {"exit": None, "error": "patch diff missing"}
    status_after = _git_status(repo)
    dry_targets = list(dry.get("target_files") or [])
    token_targets = list(token.get("target_files") or [])
    checks = {
        "token_valid": validation.status == "VALID_HUMAN_APPROVAL_TOKEN",
        "dry_run_passed": dry.get("status") == "PASS_MAIN_PATCH_DRY_RUN",
        "patch_diff_exists": patch_path.is_file() and bool(patch_text.strip()),
        "patch_sha256_available": patch_path.is_file(),
        "targets_match_dry_run": sorted(target_files) == sorted(dry_targets),
        "targets_match_token": sorted(target_files) == sorted(token_targets),
        "git_apply_check_passed": apply_check.get("exit") == 0,
        "worktree_status_unchanged": status_before == status_after,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    transaction_path: Path | None = None
    rollback_path: Path | None = None
    if not blockers:
        rollback = _build_rollback_package(repo_root=repo, patch_diff=patch_path, target_files=target_files)
        rollback_path = out / "main_patch_rollback_package.json"
        rollback_path.write_text(json.dumps(rollback, ensure_ascii=False, indent=2), encoding="utf-8")
        transaction = {
            "schema": TRANSACTION_SCHEMA,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "READY_FOR_APPROVED_MAIN_PATCH_TRANSACTION",
            "token": str(Path(token_path).expanduser()),
            "token_hash": token.get("token_hash"),
            "dry_run_result": str(dry_path),
            "dry_run_sha256": _sha256_file(dry_path),
            "patch_diff": str(patch_path),
            "patch_diff_sha256": _sha256_file(patch_path),
            "repo_root": str(repo),
            "repo_head": _git_head(repo),
            "target_files": target_files,
            "rollback_package": str(rollback_path),
            "allowed_next_command": "separate explicitly authorized transaction runner may apply patch; this module does not",
            "forbidden_by_this_gate": ["git apply", "git commit", "GeneDB mutation", "provider claim", "full AGI claim"],
            "boundary": "Prepared transaction package only; no mutation performed.",
        }
        transaction_path = out / "approved_main_patch_transaction_package.json"
        transaction_path.write_text(json.dumps(transaction, ensure_ascii=False, indent=2), encoding="utf-8")
    status = "READY_APPROVED_MAIN_PATCH_TRANSACTION_PACKAGE" if not blockers else "BLOCKED_APPROVED_MAIN_PATCH_TRANSACTION"
    return ApprovedMainPatchTransactionResult(
        schema="PGGArchonApprovedMainPatchTransactionResult/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        token_path=str(Path(token_path).expanduser()),
        dry_run_result=str(dry_path),
        patch_diff=str(patch_path),
        repo_root=str(repo),
        repo_head=_git_head(repo),
        target_files=target_files,
        checks=checks,
        blockers=blockers,
        transaction_package=str(transaction_path) if transaction_path else None,
        rollback_package=str(rollback_path) if rollback_path else None,
        git_apply_check=apply_check,
        git_status_before=status_before,
        git_status_after=status_after,
        next_action=(
            "requires separate explicit transaction runner authorization before any main-worktree mutation"
            if status == "READY_APPROVED_MAIN_PATCH_TRANSACTION_PACKAGE"
            else "resolve blockers before approved main patch transaction"
        ),
        boundary="Prepare-only transaction gate; git apply --check only, no patch application, no commit, no GeneDB mutation, no provider calls, no full AGI proof.",
    )


def write_approved_main_patch_transaction_result(
    *,
    token_path: str | Path,
    repo_root: str | Path,
    output_dir: str | Path,
    dry_run_result: str | Path | None = None,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    result = prepare_approved_main_patch_transaction(token_path=token_path, repo_root=repo_root, output_dir=out, dry_run_result=dry_run_result)
    path = out / "approved_main_patch_transaction_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "result": str(path),
        "status": result.status,
        "blockers": result.blockers,
        "transaction_package": result.transaction_package,
        "rollback_package": result.rollback_package,
        "target_files": result.target_files,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare gated approved main patch transaction package.")
    parser.add_argument("--token", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dry-run-result")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(write_approved_main_patch_transaction_result(token_path=args.token, repo_root=args.repo_root, output_dir=args.output_dir, dry_run_result=args.dry_run_result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
