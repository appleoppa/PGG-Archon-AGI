"""PGG Archon main worktree patch gate.

Boundary: read-only gate for deciding whether a promotion readiness package may
proceed to a main-worktree patch review. It does not apply patches, commit, or
mutate GeneDB.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


ALLOWED_PATCH_PREFIXES = ("tests/fixtures/", "tests/")


@dataclass(frozen=True)
class MainPatchGateResult:
    schema: str
    status: str
    readiness_package: str
    patch_diff: str
    target_files: list[str]
    checks: dict[str, bool]
    blockers: list[str]
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


def _parse_diff_targets(diff_text: str) -> list[str]:
    targets: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                b_path = parts[3]
                if b_path.startswith("b/"):
                    targets.append(b_path[2:])
    return targets


def evaluate_main_patch_gate(readiness_package: str | Path) -> MainPatchGateResult:
    package_path = Path(readiness_package).expanduser()
    package = _load_json(package_path)
    diff_path = Path(str(package.get("patch_diff") or "")).expanduser()
    diff_text = diff_path.read_text(encoding="utf-8") if diff_path.is_file() else ""
    target_files = _parse_diff_targets(diff_text)
    raw_readiness_checks = package.get("readiness_checks")
    readiness_checks: dict[str, Any] = raw_readiness_checks if isinstance(raw_readiness_checks, dict) else {}
    checks = {
        "package_ready": package.get("status") == "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW",
        "no_package_blockers": not package.get("blockers"),
        "patch_diff_exists": diff_path.is_file() and bool(diff_text.strip()),
        "targets_present": bool(target_files),
        "targets_allowed": bool(target_files) and all(path.startswith(ALLOWED_PATCH_PREFIXES) for path in target_files),
        "readiness_patch_apply_passed": readiness_checks.get("patch_apply_passed") is True,
        "readiness_regression_tasks_exists": readiness_checks.get("regression_tasks_exists") is True,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW" if not blockers else "BLOCKED_MAIN_PATCH_GATE"
    return MainPatchGateResult(
        schema="PGGArchonMainPatchGateResult/v1",
        status=status,
        readiness_package=str(package_path),
        patch_diff=str(diff_path),
        target_files=target_files,
        checks=checks,
        blockers=blockers,
        next_action=(
            "run explicit dry-run apply/review; main patch still requires separate authorization"
            if status == "READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW"
            else "resolve blockers before any main worktree patch"
        ),
        boundary="Read-only main patch gate; no patch applied, no commit, no GeneDB mutation, no full AGI proof.",
    )


def write_main_patch_gate_result(*, readiness_package: str | Path, output_dir: str | Path) -> dict[str, Any]:
    result = evaluate_main_patch_gate(readiness_package)
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "main_patch_gate_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers, "target_files": result.target_files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate read-only PGG main patch gate.")
    parser.add_argument("--readiness-package", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(write_main_patch_gate_result(readiness_package=args.readiness_package, output_dir=args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
