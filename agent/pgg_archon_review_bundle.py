"""PGG Archon review bundle gate.

Boundary: combines existing read-only readiness, main-patch gate, and LLM quorum
evidence into a single review bundle. It does not call providers, apply patches,
commit, mutate GeneDB, or claim AGI completion.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class ReviewBundleResult:
    schema: str
    status: str
    generated_at: str
    readiness_package: str
    main_patch_gate_result: str
    llm_quorum_gate_result: str
    checks: dict[str, bool]
    blockers: list[str]
    target_files: list[str]
    visible_pass_count: int | None
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


def evaluate_review_bundle(
    *,
    readiness_package: str | Path,
    main_patch_gate_result: str | Path,
    llm_quorum_gate_result: str | Path,
) -> ReviewBundleResult:
    readiness_path = Path(readiness_package).expanduser()
    main_gate_path = Path(main_patch_gate_result).expanduser()
    quorum_path = Path(llm_quorum_gate_result).expanduser()
    readiness = _load_json(readiness_path)
    main_gate = _load_json(main_gate_path)
    quorum = _load_json(quorum_path)
    checks = {
        "readiness_ready": readiness.get("status") == "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW",
        "readiness_no_blockers": not readiness.get("blockers"),
        "main_patch_gate_ready": main_gate.get("status") == "READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW",
        "main_patch_gate_no_blockers": not main_gate.get("blockers"),
        "llm_quorum_pass": quorum.get("status") == "PASS_QUORUM",
        "llm_quorum_no_blockers": not quorum.get("blockers"),
        "llm_visible_pass_threshold": int(quorum.get("visible_pass_count") or 0) >= int(quorum.get("required_pass_count") or 2),
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "READY_FOR_HUMAN_MAIN_PATCH_REVIEW" if not blockers else "BLOCKED_REVIEW_BUNDLE"
    return ReviewBundleResult(
        schema="PGGArchonReviewBundleResult/v1",
        status=status,
        generated_at=datetime.now(timezone.utc).isoformat(),
        readiness_package=str(readiness_path),
        main_patch_gate_result=str(main_gate_path),
        llm_quorum_gate_result=str(quorum_path),
        checks=checks,
        blockers=blockers,
        target_files=list(main_gate.get("target_files") or []),
        visible_pass_count=quorum.get("visible_pass_count"),
        next_action=(
            "human may review the dry-run patch bundle; still no automatic main patch or GeneDB mutation"
            if status == "READY_FOR_HUMAN_MAIN_PATCH_REVIEW"
            else "resolve blockers before review or patch application"
        ),
        boundary="Read-only review bundle; no provider calls, no patch application, no commit, no GeneDB mutation, no full AGI proof.",
    )


def write_review_bundle(
    *,
    readiness_package: str | Path,
    main_patch_gate_result: str | Path,
    llm_quorum_gate_result: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    result = evaluate_review_bundle(
        readiness_package=readiness_package,
        main_patch_gate_result=main_patch_gate_result,
        llm_quorum_gate_result=llm_quorum_gate_result,
    )
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "review_bundle_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers, "target_files": result.target_files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build read-only PGG Archon review bundle.")
    parser.add_argument("--readiness-package", required=True)
    parser.add_argument("--main-patch-gate", required=True)
    parser.add_argument("--llm-quorum-gate", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(write_review_bundle(
        readiness_package=args.readiness_package,
        main_patch_gate_result=args.main_patch_gate,
        llm_quorum_gate_result=args.llm_quorum_gate,
        output_dir=args.output_dir,
    ), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
