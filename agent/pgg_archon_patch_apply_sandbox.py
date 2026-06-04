"""PGG Archon isolated patch apply sandbox.

Boundary: applies a narrowly-scoped candidate patch only inside a temporary git
worktree, records the diff and verification results, and never commits or mutates
the main worktree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PatchApplySandboxResult:
    schema: str
    candidate_id: str
    generated_at: str
    status: str
    worktree_path: str
    patch_type: str
    changed_files: list[str]
    diff_path: str
    verification_results: list[dict[str, Any]]
    promotion_gate: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _first_candidate(path: str | Path) -> dict[str, Any]:
    data = _load_json(path)
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidate batch has no candidates")
    first = candidates[0]
    if not isinstance(first, dict):
        raise ValueError("candidate is not an object")
    return first


def _run(cmd: Sequence[str] | str, *, cwd: Path, timeout: int = 120, shell: bool = False) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, shell=shell)
        return {"cmd": cmd if isinstance(cmd, str) else list(cmd), "exit": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:]}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": cmd if isinstance(cmd, str) else list(cmd), "exit": None, "error": repr(exc)}


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value)[:80] or "candidate"


def _create_worktree(repo_root: Path, worktree_path: Path) -> dict[str, Any]:
    if worktree_path.exists():
        shutil.rmtree(worktree_path)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    result = _run(["git", "worktree", "add", "--detach", str(worktree_path), "HEAD"], cwd=repo_root, timeout=120)
    return result


def _remove_worktree(repo_root: Path, worktree_path: Path) -> dict[str, Any]:
    return _run(["git", "worktree", "remove", "--force", str(worktree_path)], cwd=repo_root, timeout=120)


def _install_regression_fixture(worktree_path: Path, regression_tasks_jsonl: Path) -> list[str]:
    target = worktree_path / "tests" / "fixtures" / "pgg_archon_regressions.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    content = regression_tasks_jsonl.read_text(encoding="utf-8")
    target.write_text(content, encoding="utf-8")
    # Intent-to-add makes the new file visible in `git diff` without staging
    # content or committing anything in the sandbox worktree.
    _run(["git", "add", "-N", str(target.relative_to(worktree_path))], cwd=worktree_path, timeout=30)
    return [str(target.relative_to(worktree_path))]


def _diff(worktree_path: Path, diff_path: Path) -> str:
    diff = _run(["git", "diff", "--", "."], cwd=worktree_path, timeout=120)
    text = diff.get("stdout", "")
    diff_path.write_text(text, encoding="utf-8")
    return text


def apply_patch_candidate_in_worktree(
    candidate_batch_path: str | Path,
    *,
    repo_root: str | Path,
    output_dir: str | Path,
    regression_tasks_jsonl: str | Path,
    keep_worktree: bool = True,
    timeout: int = 120,
) -> PatchApplySandboxResult:
    repo = Path(repo_root).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    candidate = _first_candidate(candidate_batch_path)
    candidate_id = str(candidate.get("candidate_id") or "candidate")
    worktree = out / f"worktree-{_safe_id(candidate_id)}"
    create_result = _create_worktree(repo, worktree)
    if create_result.get("exit") != 0:
        return PatchApplySandboxResult(
            schema="PGGArchonPatchApplySandboxResult/v1",
            candidate_id=candidate_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            status="BLOCKED_WORKTREE_CREATE_FAILED",
            worktree_path=str(worktree),
            patch_type="regression_fixture_install",
            changed_files=[],
            diff_path="",
            verification_results=[create_result],
            promotion_gate="fix_worktree_creation_before_patch",
            boundary="No patch applied to main worktree.",
        )

    changed_files = _install_regression_fixture(worktree, Path(regression_tasks_jsonl).expanduser())
    diff_path = out / "candidate.diff"
    diff_text = _diff(worktree, diff_path)
    verification_commands = [str(x) for x in candidate.get("verification_commands", []) or []]
    verification_results = [_run(cmd, cwd=worktree, timeout=timeout, shell=True) for cmd in verification_commands]
    commands_ok = all(item.get("exit") == 0 for item in verification_results)
    status = "PASS_PATCH_SANDBOX" if diff_text.strip() and commands_ok else "WATCH"
    if not keep_worktree:
        _remove_worktree(repo, worktree)
    return PatchApplySandboxResult(
        schema="PGGArchonPatchApplySandboxResult/v1",
        candidate_id=candidate_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        worktree_path=str(worktree),
        patch_type="regression_fixture_install",
        changed_files=changed_files,
        diff_path=str(diff_path),
        verification_results=verification_results,
        promotion_gate="main_worktree_apply_requires_diff_review_tests_manifest_readback_and_scoped_commit" if status == "PASS_PATCH_SANDBOX" else "fix_patch_sandbox_before_main_apply",
        boundary="Patch applied only inside temporary git worktree; main worktree untouched, no GeneDB promotion.",
    )


def write_patch_apply_sandbox_result(
    candidate_batch_path: str | Path,
    *,
    repo_root: str | Path,
    output_dir: str | Path,
    regression_tasks_jsonl: str | Path,
    keep_worktree: bool = True,
    timeout: int = 120,
) -> dict[str, Any]:
    result = apply_patch_candidate_in_worktree(
        candidate_batch_path,
        repo_root=repo_root,
        output_dir=output_dir,
        regression_tasks_jsonl=regression_tasks_jsonl,
        keep_worktree=keep_worktree,
        timeout=timeout,
    )
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "patch_apply_sandbox_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "diff_path": result.diff_path, "worktree_path": result.worktree_path}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a read-only patch candidate in an isolated git worktree.")
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--regression-tasks-jsonl", required=True)
    parser.add_argument("--remove-worktree", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_patch_apply_sandbox_result(
        args.candidates,
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        regression_tasks_jsonl=args.regression_tasks_jsonl,
        keep_worktree=not args.remove_worktree,
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
