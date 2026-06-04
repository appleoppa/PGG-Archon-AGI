"""PGG Archon regression + rollback verifier for approved patch packages.

Boundary: verifies an approved main patch transaction package inside a temporary
git worktree. It applies and reverses the candidate diff only in the temporary
worktree, runs bounded verification commands, and never mutates the main
worktree, commits, mutates GeneDB, calls providers, or claims AGI completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class RegressionRollbackVerificationResult:
    schema: str
    generated_at: str
    status: str
    transaction_package: str
    rollback_package: str | None
    repo_root: str
    temp_worktree: str | None
    target_files: list[str]
    checks: dict[str, bool]
    blockers: list[str]
    apply_result: dict[str, Any]
    verification_results: list[dict[str, Any]]
    rollback_result: dict[str, Any]
    git_status_before: str
    git_status_after: str
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


def _run(cmd: list[str], *, cwd: Path, timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        return {"cmd": cmd, "exit": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": cmd, "exit": None, "error": repr(exc)}


def _git_status(repo_root: Path) -> str:
    return str(_run(["git", "status", "--short"], cwd=repo_root, timeout=30).get("stdout") or "")


def _target_hashes(root: Path, targets: list[str]) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for target in targets:
        p = root / target
        hashes[target] = _sha256_file(p) if p.is_file() else None
    return hashes


def verify_regression_and_rollback(
    *,
    transaction_package: str | Path,
    repo_root: str | Path,
    keep_worktree: bool = False,
    verification_commands: Sequence[Sequence[str]] | None = None,
) -> RegressionRollbackVerificationResult:
    repo = Path(repo_root).expanduser()
    tx_path = Path(transaction_package).expanduser()
    tx = _load_json(tx_path)
    rollback_path = Path(str(tx.get("rollback_package") or "")).expanduser()
    rollback = _load_json(rollback_path) if rollback_path.is_file() else {}
    patch_path = Path(str(tx.get("patch_diff") or "")).expanduser()
    targets = list(tx.get("target_files") or [])
    main_status_before = _git_status(repo)
    tmp_dir: Path | None = None
    apply_result: dict[str, Any] = {"exit": None, "error": "not run"}
    rollback_result: dict[str, Any] = {"exit": None, "error": "not run"}
    verification_results: list[dict[str, Any]] = []
    checks: dict[str, bool] = {
        "transaction_ready": tx.get("status") == "READY_FOR_APPROVED_MAIN_PATCH_TRANSACTION",
        "rollback_package_exists": rollback_path.is_file(),
        "patch_diff_exists": patch_path.is_file(),
        "patch_diff_sha256_matches": patch_path.is_file() and tx.get("patch_diff_sha256") == _sha256_file(patch_path),
        "rollback_schema_valid": rollback.get("schema") == "PGGArchonMainPatchRollbackPackage/v1",
        "target_files_present": bool(targets),
    }
    blockers = [name for name, ok in checks.items() if not ok]
    if not blockers:
        tmp_dir = Path(tempfile.mkdtemp(prefix="pgg-v3p3-worktree-"))
        add = _run(["git", "worktree", "add", "--detach", str(tmp_dir), "HEAD"], cwd=repo, timeout=120)
        checks["temp_worktree_created"] = add.get("exit") == 0
        if add.get("exit") != 0:
            blockers.append("temp_worktree_created")
        else:
            before_hashes = _target_hashes(tmp_dir, targets)
            apply_result = _run(["git", "apply", str(patch_path)], cwd=tmp_dir, timeout=120)
            checks["patch_applied_in_temp_worktree"] = apply_result.get("exit") == 0
            if apply_result.get("exit") == 0:
                after_apply_hashes = _target_hashes(tmp_dir, targets)
                checks["target_hashes_changed_after_apply"] = before_hashes != after_apply_hashes
                if verification_commands is not None:
                    commands = list(verification_commands)
                else:
                    commands = []
                    if (tmp_dir / "agent" / "pgg_archon_approved_main_patch_transaction.py").is_file():
                        commands.append(["python", "-m", "py_compile", "agent/pgg_archon_approved_main_patch_transaction.py"])
                    commands.append(["git", "diff", "--check"])
                for cmd in commands:
                    verification_results.append(_run(list(cmd), cwd=tmp_dir, timeout=180))
                checks["verification_commands_passed"] = all(r.get("exit") == 0 for r in verification_results)
                rollback_result = _run(["git", "apply", "-R", str(patch_path)], cwd=tmp_dir, timeout=120)
                checks["rollback_applied_in_temp_worktree"] = rollback_result.get("exit") == 0
                after_rollback_hashes = _target_hashes(tmp_dir, targets)
                checks["target_hashes_restored_after_rollback"] = before_hashes == after_rollback_hashes
            else:
                checks["target_hashes_changed_after_apply"] = False
                checks["verification_commands_passed"] = False
                checks["rollback_applied_in_temp_worktree"] = False
                checks["target_hashes_restored_after_rollback"] = False
            blockers = [name for name, ok in checks.items() if not ok]
    main_status_after = _git_status(repo)
    checks["main_worktree_status_unchanged"] = main_status_before == main_status_after
    blockers = [name for name, ok in checks.items() if not ok]
    status = "PASS_REGRESSION_ROLLBACK_VERIFICATION" if not blockers else "BLOCKED_REGRESSION_ROLLBACK_VERIFICATION"
    temp_path = str(tmp_dir) if tmp_dir else None
    if tmp_dir and not keep_worktree:
        _run(["git", "worktree", "remove", "--force", str(tmp_dir)], cwd=repo, timeout=120)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        temp_path = None
    return RegressionRollbackVerificationResult(
        schema="PGGArchonRegressionRollbackVerificationResult/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        transaction_package=str(tx_path),
        rollback_package=str(rollback_path) if rollback_path else None,
        repo_root=str(repo),
        temp_worktree=temp_path,
        target_files=targets,
        checks=checks,
        blockers=blockers,
        apply_result=apply_result,
        verification_results=verification_results,
        rollback_result=rollback_result,
        git_status_before=main_status_before,
        git_status_after=main_status_after,
        boundary="Temporary-worktree verification only; no main worktree mutation, no commit, no GeneDB mutation, no provider calls, no full AGI proof.",
    )


def write_regression_rollback_verification_result(*, transaction_package: str | Path, repo_root: str | Path, output_dir: str | Path, keep_worktree: bool = False) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    result = verify_regression_and_rollback(transaction_package=transaction_package, repo_root=repo_root, keep_worktree=keep_worktree)
    path = out / "regression_rollback_verification_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers, "target_files": result.target_files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify approved patch regression and rollback in a temporary worktree.")
    parser.add_argument("--transaction-package", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--keep-worktree", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(write_regression_rollback_verification_result(transaction_package=args.transaction_package, repo_root=args.repo_root, output_dir=args.output_dir, keep_worktree=args.keep_worktree), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
