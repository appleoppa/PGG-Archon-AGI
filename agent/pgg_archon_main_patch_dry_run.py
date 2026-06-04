"""PGG Archon main patch dry-run simulator.

Boundary: validates that a reviewed patch diff can be applied to the main
worktree using `git apply --check` only. It never applies the patch, commits,
mutates GeneDB, calls providers, or claims AGI completion.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class MainPatchDryRunResult:
    schema: str
    status: str
    review_bundle: str
    patch_diff: str
    repo_root: str
    target_files: list[str]
    checks: dict[str, bool]
    blockers: list[str]
    git_apply_check: dict[str, Any]
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


def _run(cmd: list[str], *, cwd: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        return {"cmd": cmd, "exit": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": cmd, "exit": None, "error": repr(exc)}


def _git_status(repo_root: Path) -> str:
    result = _run(["git", "status", "--short"], cwd=repo_root, timeout=30)
    return str(result.get("stdout") or "")


def _diff_targets(diff_text: str) -> list[str]:
    targets: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                targets.append(parts[3][2:])
    return targets


def evaluate_main_patch_dry_run(*, review_bundle: str | Path, repo_root: str | Path) -> MainPatchDryRunResult:
    repo = Path(repo_root).expanduser()
    bundle_path = Path(review_bundle).expanduser()
    bundle = _load_json(bundle_path)
    readiness = _load_json(bundle["readiness_package"])
    patch_path = Path(str(readiness.get("patch_diff") or "")).expanduser()
    diff_text = patch_path.read_text(encoding="utf-8") if patch_path.is_file() else ""
    target_files = _diff_targets(diff_text)
    status_before = _git_status(repo)
    apply_check = _run(["git", "apply", "--check", str(patch_path)], cwd=repo, timeout=60) if patch_path.is_file() else {"exit": None, "error": "patch diff missing"}
    status_after = _git_status(repo)
    checks = {
        "review_bundle_ready": bundle.get("status") == "READY_FOR_HUMAN_MAIN_PATCH_REVIEW",
        "review_bundle_no_blockers": not bundle.get("blockers"),
        "patch_diff_exists": patch_path.is_file() and bool(diff_text.strip()),
        "targets_match_bundle": sorted(target_files) == sorted(list(bundle.get("target_files") or [])),
        "git_apply_check_passed": apply_check.get("exit") == 0,
        "worktree_status_unchanged": status_before == status_after,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "PASS_MAIN_PATCH_DRY_RUN" if not blockers else "BLOCKED_MAIN_PATCH_DRY_RUN"
    return MainPatchDryRunResult(
        schema="PGGArchonMainPatchDryRunResult/v1",
        status=status,
        review_bundle=str(bundle_path),
        patch_diff=str(patch_path),
        repo_root=str(repo),
        target_files=target_files,
        checks=checks,
        blockers=blockers,
        git_apply_check=apply_check,
        git_status_before=status_before,
        git_status_after=status_after,
        boundary="Dry-run only: git apply --check; no patch application, no commit, no GeneDB mutation, no provider calls, no full AGI proof.",
    )


def write_main_patch_dry_run(*, review_bundle: str | Path, repo_root: str | Path, output_dir: str | Path) -> dict[str, Any]:
    result = evaluate_main_patch_dry_run(review_bundle=review_bundle, repo_root=repo_root)
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "main_patch_dry_run_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers, "target_files": result.target_files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only main patch dry-run simulator.")
    parser.add_argument("--review-bundle", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(write_main_patch_dry_run(review_bundle=args.review_bundle, repo_root=args.repo_root, output_dir=args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
