"""PGG Archon promotion readiness package builder.

Boundary: read-only package assembly after temp-worktree patch evidence. It does not
apply main patches, mutate GeneDB, or promote genes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class PromotionReadinessPackage:
    schema: str
    generated_at: str
    status: str
    source_queue: str
    source_queue_sha256: str
    proposal_batch: str
    regression_fixtures: str
    regression_tasks_jsonl: str
    patch_candidates: str
    sandbox_results: str
    patch_apply_result: str
    patch_diff: str
    readiness_checks: dict[str, bool]
    blockers: list[str]
    next_action: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {p}")
    return data


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).expanduser().read_bytes()).hexdigest()


def build_promotion_readiness_package(
    *,
    source_queue: str | Path,
    proposal_batch: str | Path,
    regression_fixtures: str | Path,
    regression_tasks_jsonl: str | Path,
    patch_candidates: str | Path,
    sandbox_results: str | Path,
    patch_apply_result: str | Path,
) -> PromotionReadinessPackage:
    queue = Path(source_queue).expanduser()
    proposal = _load(proposal_batch)
    fixtures = _load(regression_fixtures)
    candidates = _load(patch_candidates)
    sandbox = _load(sandbox_results)
    apply_result = _load(patch_apply_result)
    diff_path = str(apply_result.get("diff_path") or "")
    checks = {
        "queue_exists": queue.is_file(),
        "proposal_count_positive": int(proposal.get("proposal_count") or len(proposal.get("proposals", []) or [])) > 0,
        "fixture_count_positive": int(fixtures.get("fixture_count") or len(fixtures.get("fixtures", []) or [])) > 0,
        "candidate_count_positive": int(candidates.get("candidate_count") or len(candidates.get("candidates", []) or [])) > 0,
        "sandbox_passed": int(sandbox.get("pass_count") or 0) > 0,
        "patch_apply_passed": apply_result.get("status") in {"PASS_PATCH_SANDBOX", "ALREADY_PATCHED_VERIFIED"},
        "patch_diff_exists": bool(diff_path) and Path(diff_path).expanduser().is_file(),
        "regression_tasks_exists": Path(regression_tasks_jsonl).expanduser().is_file(),
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW" if not blockers else "BLOCKED_READINESS_PACKAGE"
    return PromotionReadinessPackage(
        schema="PGGArchonPromotionReadinessPackage/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        source_queue=str(queue),
        source_queue_sha256=_sha(queue) if queue.is_file() else "",
        proposal_batch=str(Path(proposal_batch).expanduser()),
        regression_fixtures=str(Path(regression_fixtures).expanduser()),
        regression_tasks_jsonl=str(Path(regression_tasks_jsonl).expanduser()),
        patch_candidates=str(Path(patch_candidates).expanduser()),
        sandbox_results=str(Path(sandbox_results).expanduser()),
        patch_apply_result=str(Path(patch_apply_result).expanduser()),
        patch_diff=diff_path,
        readiness_checks=checks,
        blockers=blockers,
        next_action="review package, apply main patch/gene candidate gate only under explicit authorization" if not blockers else "resolve blockers before any main patch or GeneDB mutation",
        boundary="Read-only readiness package; no main worktree mutation, no GeneDB mutation, no full AGI proof.",
    )


def write_promotion_readiness_package(*, output_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
    pkg = build_promotion_readiness_package(**kwargs)
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "promotion_readiness_package.json"
    path.write_text(json.dumps(pkg.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"package": str(path), "status": pkg.status, "blockers": pkg.blockers}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build read-only PGG promotion readiness package.")
    parser.add_argument("--source-queue", required=True)
    parser.add_argument("--proposal-batch", required=True)
    parser.add_argument("--regression-fixtures", required=True)
    parser.add_argument("--regression-tasks-jsonl", required=True)
    parser.add_argument("--patch-candidates", required=True)
    parser.add_argument("--sandbox-results", required=True)
    parser.add_argument("--patch-apply-result", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_promotion_readiness_package(
        output_dir=args.output_dir,
        source_queue=args.source_queue,
        proposal_batch=args.proposal_batch,
        regression_fixtures=args.regression_fixtures,
        regression_tasks_jsonl=args.regression_tasks_jsonl,
        patch_candidates=args.patch_candidates,
        sandbox_results=args.sandbox_results,
        patch_apply_result=args.patch_apply_result,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
