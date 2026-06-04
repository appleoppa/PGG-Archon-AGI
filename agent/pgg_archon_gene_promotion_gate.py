"""PGG Archon GeneDB promotion audit gate.

Boundary: read-only gate that decides whether a GeneDB candidate may proceed to
promotion review. It never promotes, edits GeneDB state, or claims full AGI.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class GenePromotionGateResult:
    schema: str
    generated_at: str
    gene_id: int
    status: str
    lifecycle_state: str
    quality_score: float | None
    required_checks: dict[str, bool]
    blockers: list[str]
    next_action: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_model_evidence(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path).expanduser()
    if not p.exists():
        return {"missing": str(p)}
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"value": data}


def evaluate_gene_promotion_gate(
    *,
    db_path: str | Path,
    gene_id: int,
    claude_evidence_path: str | Path | None = None,
    required_tests_passed: bool = False,
    manifest_updated: bool = False,
) -> GenePromotionGateResult:
    db = Path(db_path).expanduser()
    con = sqlite3.connect(db)
    cur = con.cursor()
    row = cur.execute("select state, quality_score, promoted_at from gene_lifecycle where gene_id=?", (gene_id,)).fetchone()
    con.close()
    if row is None:
        return GenePromotionGateResult(
            schema="PGGArchonGenePromotionGateResult/v1",
            generated_at=datetime.now(timezone.utc).isoformat(),
            gene_id=gene_id,
            status="BLOCKED_GENE_NOT_FOUND",
            lifecycle_state="missing",
            quality_score=None,
            required_checks={},
            blockers=["gene_lifecycle row missing"],
            next_action="insert candidate before promotion audit",
            boundary="Read-only gate; no GeneDB mutation.",
        )
    state, quality, promoted_at = row
    claude = _load_model_evidence(claude_evidence_path)
    claude_visible = claude.get("status") == "ok_visible" and int(claude.get("visible_output_chars") or 0) > 0
    checks = {
        "candidate_state": state == "candidate",
        "not_already_promoted": promoted_at is None,
        "quality_score_min_0_80": quality is not None and float(quality) >= 0.80,
        "required_tests_passed": required_tests_passed,
        "manifest_updated": manifest_updated,
        "claude_visible_verification": claude_visible,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "READY_FOR_PROMOTION_REVIEW" if not blockers else "BLOCKED_PROMOTION_REVIEW"
    return GenePromotionGateResult(
        schema="PGGArchonGenePromotionGateResult/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        gene_id=gene_id,
        status=status,
        lifecycle_state=str(state),
        quality_score=float(quality) if quality is not None else None,
        required_checks=checks,
        blockers=blockers,
        next_action="run independent model verification and promotion_chain transaction" if status == "READY_FOR_PROMOTION_REVIEW" else "resolve blockers before promotion; do not set promoted state",
        boundary="Read-only promotion audit gate; no promotion, no GeneDB mutation, no full AGI proof.",
    )


def write_gene_promotion_gate_result(
    *,
    db_path: str | Path,
    gene_id: int,
    output_dir: str | Path,
    claude_evidence_path: str | Path | None = None,
    required_tests_passed: bool = False,
    manifest_updated: bool = False,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    result = evaluate_gene_promotion_gate(
        db_path=db_path,
        gene_id=gene_id,
        claude_evidence_path=claude_evidence_path,
        required_tests_passed=required_tests_passed,
        manifest_updated=manifest_updated,
    )
    path = out / "gene_promotion_gate_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate read-only GeneDB promotion audit gate.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--gene-id", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--claude-evidence")
    parser.add_argument("--tests-passed", action="store_true")
    parser.add_argument("--manifest-updated", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_gene_promotion_gate_result(
        db_path=args.db,
        gene_id=args.gene_id,
        output_dir=args.output_dir,
        claude_evidence_path=args.claude_evidence,
        required_tests_passed=args.tests_passed,
        manifest_updated=args.manifest_updated,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
