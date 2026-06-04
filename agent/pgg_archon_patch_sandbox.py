"""PGG Archon patch sandbox readiness runner.

Boundary: evaluates read-only patch candidates in an isolated evidence directory.
It checks target surfaces and optionally runs declared verification commands, but
it does not apply patches, edit files, write GeneDB, or mutate scheduler/security/provider boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PatchSandboxResult:
    schema: str
    candidate_id: str
    generated_at: str
    status: str
    target_surface_checks: list[dict[str, Any]]
    verification_results: list[dict[str, Any]]
    patch_applicable: bool
    next_gate: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_candidate_batch(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected patch candidate batch object: {path}")
    return data


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_surfaces(candidate: Mapping[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for raw in candidate.get("target_surfaces", []) or []:
        rel = str(raw)
        path = (repo_root / rel).resolve()
        inside_repo = str(path).startswith(str(repo_root.resolve()))
        checks.append({
            "surface": rel,
            "inside_repo": inside_repo,
            "exists": path.exists() if inside_repo else False,
            "is_file": path.is_file() if inside_repo else False,
            "is_dir": path.is_dir() if inside_repo else False,
            "sha256": _file_sha256(path) if inside_repo else None,
        })
    return checks


def _run_verification(command: str, repo_root: Path, timeout: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(command, shell=True, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout)
        return {
            "command": command,
            "exit": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-2000:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"command": command, "exit": None, "error": repr(exc)}


def evaluate_patch_candidate(
    candidate: Mapping[str, Any],
    *,
    repo_root: str | Path,
    run_commands: bool = True,
    timeout: int = 120,
) -> PatchSandboxResult:
    root = Path(repo_root).expanduser().resolve()
    surfaces = _check_surfaces(candidate, root)
    commands = [str(x) for x in candidate.get("verification_commands", []) or []]
    verification = [_run_verification(cmd, root, timeout) for cmd in commands] if run_commands else []
    surfaces_ok = bool(surfaces) and all(item.get("inside_repo") and (item.get("exists")) for item in surfaces)
    commands_ok = all(item.get("exit") == 0 for item in verification) if run_commands else True
    status = "PASS_READY_FOR_ISOLATED_PATCH" if surfaces_ok and commands_ok else "WATCH"
    return PatchSandboxResult(
        schema="PGGArchonPatchSandboxResult/v1",
        candidate_id=str(candidate.get("candidate_id") or ""),
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        target_surface_checks=surfaces,
        verification_results=verification,
        patch_applicable=status == "PASS_READY_FOR_ISOLATED_PATCH",
        next_gate="apply_patch_only_in_temp_worktree_with_explicit_diff_and_rerun_verification" if status == "PASS_READY_FOR_ISOLATED_PATCH" else "fix_candidate_or_verification_before_patch",
        boundary="Sandbox readiness only; no patch applied, no files edited, no GeneDB promotion.",
    )


def evaluate_patch_candidate_batch(
    candidate_batch_path: str | Path,
    *,
    repo_root: str | Path,
    run_commands: bool = True,
    timeout: int = 120,
    limit: int | None = None,
) -> list[PatchSandboxResult]:
    batch = _load_candidate_batch(candidate_batch_path)
    candidates = batch.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("candidate batch must contain list field: candidates")
    selected = [item for item in candidates if isinstance(item, dict)]
    if limit is not None:
        selected = selected[:limit]
    return [evaluate_patch_candidate(item, repo_root=repo_root, run_commands=run_commands, timeout=timeout) for item in selected]


def write_patch_sandbox_results(
    candidate_batch_path: str | Path,
    *,
    repo_root: str | Path,
    output_dir: str | Path,
    run_commands: bool = True,
    timeout: int = 120,
    limit: int | None = None,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    results = evaluate_patch_candidate_batch(
        candidate_batch_path,
        repo_root=repo_root,
        run_commands=run_commands,
        timeout=timeout,
        limit=limit,
    )
    payload = {
        "schema": "PGGArchonPatchSandboxBatch/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_batch_path": str(Path(candidate_batch_path).expanduser()),
        "repo_root": str(Path(repo_root).expanduser().resolve()),
        "result_count": len(results),
        "pass_count": sum(1 for item in results if item.status == "PASS_READY_FOR_ISOLATED_PATCH"),
        "results": [item.to_json_dict() for item in results],
        "boundary": "Read-only sandbox readiness; no patch applied, no files edited, no GeneDB writes.",
    }
    batch_path = out / "patch_sandbox_results.json"
    jsonl_path = out / "patch_sandbox_results.jsonl"
    batch_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item.to_json_dict(), ensure_ascii=False) + "\n")
    return {"batch": str(batch_path), "jsonl": str(jsonl_path), "result_count": len(results), "pass_count": payload["pass_count"]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate read-only patch candidate sandbox readiness.")
    parser.add_argument("--candidates", required=True, help="Path to patch_candidates.json")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-run-commands", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_patch_sandbox_results(
        args.candidates,
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        run_commands=not args.no_run_commands,
        timeout=args.timeout,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
