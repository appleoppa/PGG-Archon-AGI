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
    alternate_evidence_path: str | Path | None = None,
    allow_alternate_when_claude_unavailable: bool = False,
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
    alternate = _load_model_evidence(alternate_evidence_path)
    claude_visible = claude.get("status") == "ok_visible" and int(claude.get("visible_output_chars") or 0) > 0
    alternate_visible = alternate.get("status") == "ok_visible" and int(alternate.get("visible_output_chars") or 0) > 0
    independent_visible_verification = claude_visible or (allow_alternate_when_claude_unavailable and alternate_visible)
    checks = {
        "candidate_state": state == "candidate",
        "not_already_promoted": promoted_at is None,
        "quality_score_min_0_80": quality is not None and float(quality) >= 0.80,
        "required_tests_passed": required_tests_passed,
        "manifest_updated": manifest_updated,
        "independent_visible_verification": independent_visible_verification,
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



@dataclass(frozen=True)
class GeneCandidateReview:
    gene_id: int
    name: str | None
    pattern_type: str | None
    lifecycle_state: str
    quality_score: float | None
    promoted_at: str | None
    decision: str
    blockers: list[str]
    duplicate_group_size: int
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenePromotionCandidateAuditResult:
    schema: str
    generated_at: str
    db: str
    status: str
    candidate_count: int
    review_ready_count: int
    llm_quorum_status: str
    required_checks: dict[str, bool]
    candidate_reviews: list[dict[str, Any]]
    blockers: list[str]
    next_action: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text_risk_blockers(name: str | None, pattern_type: str | None, snippet: str | None) -> list[str]:
    text = " ".join(x or "" for x in [name, pattern_type, snippet]).lower()
    blockers: list[str] = []
    if any(token in text for token in ["auto_core_takeover", "core_takeover", "safe_core_takeover"]):
        blockers.append("core_takeover_requires_explicit_human_authorization")
    if any(token in text for token in ["hold_sidecar_only_no_core_mutation", "forbidden", "rollback_plan_present\": false"]):
        blockers.append("candidate_contains_unresolved_safety_hold")
    if any(token in text for token in ["phase3_ars_cycle_gate", "periodic_ars"]):
        blockers.append("phase3_ars_cycle_candidate_requires_duplicate_staleness_review")
    return blockers


def _load_llm_quorum_summary(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"status": "MISSING_LLM_QUORUM", "visible_pass_count": 0, "required_pass_count": 2}
    data = _load_model_evidence(path)
    if data.get("missing"):
        return {"status": "MISSING_LLM_QUORUM", "visible_pass_count": 0, "required_pass_count": 2}
    if "status" in data and "visible_pass_count" in data:
        return data
    decision = data.get("decision")
    visible_pass_count = int(data.get("visible_pass_count") or 0)
    return {
        "status": "PASS_QUORUM" if decision == "PROCEED_PROMOTION_TRANSACTION" and visible_pass_count >= 2 else "BLOCKED_QUORUM",
        "visible_pass_count": visible_pass_count,
        "required_pass_count": 2,
    }


def evaluate_all_gene_candidates_promotion_gate(
    *,
    db_path: str | Path,
    llm_quorum_path: str | Path | None = None,
    quality_threshold: float = 0.80,
) -> GenePromotionCandidateAuditResult:
    """Review every GeneDB lifecycle candidate without mutating GeneDB.

    This gate separates candidate audit from promotion transaction. It can say a
    row is ready for promotion review, but it never sets state/promoted_at.
    """
    db = Path(db_path).expanduser()
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = cur.execute(
        """select l.gene_id,l.state,l.quality_score,l.promoted_at,l.candidate_at,
                  g.name,g.pattern_type,g.source_repo,g.code_snippet
           from gene_lifecycle l left join genes g on g.id=l.gene_id
           where l.state='candidate'
           order by coalesce(l.quality_score,0) desc, l.gene_id desc"""
    ).fetchall()
    con.close()

    duplicate_keys: dict[str, int] = {}
    row_keys: dict[int, str] = {}
    for row in rows:
        key = "|".join(str(row[k] or "").strip().lower() for k in ["name", "pattern_type"])
        row_keys[int(row["gene_id"])] = key
        duplicate_keys[key] = duplicate_keys.get(key, 0) + 1

    llm = _load_llm_quorum_summary(llm_quorum_path)
    llm_status = str(llm.get("status") or "UNKNOWN")
    llm_passed = llm_status in {"PASS_QUORUM", "PROCEED_PROMOTION_TRANSACTION"}

    reviews: list[GeneCandidateReview] = []
    for row in rows:
        gene_id = int(row["gene_id"])
        quality = row["quality_score"]
        quality_f = float(quality) if quality is not None else None
        blockers: list[str] = []
        if row["state"] != "candidate":
            blockers.append("not_candidate_state")
        if row["promoted_at"] is not None:
            blockers.append("already_promoted")
        if quality_f is None or quality_f < quality_threshold:
            blockers.append("quality_score_below_threshold")
        duplicate_size = duplicate_keys.get(row_keys[gene_id], 1)
        if duplicate_size > 1:
            blockers.append("duplicate_candidate_group")
        blockers.extend(_text_risk_blockers(row["name"], row["pattern_type"], row["code_snippet"]))
        if not llm_passed:
            blockers.append("llm_quorum_not_passed")
        decision = "PROMOTION_REVIEW_READY" if not blockers else "BLOCKED"
        reviews.append(GeneCandidateReview(
            gene_id=gene_id,
            name=row["name"],
            pattern_type=row["pattern_type"],
            lifecycle_state=str(row["state"]),
            quality_score=quality_f,
            promoted_at=row["promoted_at"],
            decision=decision,
            blockers=blockers,
            duplicate_group_size=duplicate_size,
            boundary="Candidate audit only; no GeneDB mutation.",
        ))

    ready_count = sum(1 for item in reviews if item.decision == "PROMOTION_REVIEW_READY")
    checks = {
        "has_candidates": bool(rows),
        "llm_quorum_passed": llm_passed,
        "at_least_one_candidate_review_ready": ready_count > 0,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "READY_FOR_PROMOTION_TRANSACTION" if not blockers else "BLOCKED_CANDIDATE_AUDIT"
    return GenePromotionCandidateAuditResult(
        schema="PGGArchonGenePromotionCandidateAuditResult/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        db=str(db),
        status=status,
        candidate_count=len(rows),
        review_ready_count=ready_count,
        llm_quorum_status=llm_status,
        required_checks=checks,
        candidate_reviews=[item.to_json_dict() for item in reviews],
        blockers=blockers,
        next_action="run bounded promotion transaction for exactly one reviewed candidate" if status == "READY_FOR_PROMOTION_TRANSACTION" else "resolve blockers; do not promote any candidate",
        boundary="Read-only all-candidate promotion gate; no promotion, no GeneDB mutation, no full AGI proof.",
    )


def write_all_gene_candidates_promotion_gate_result(
    *,
    db_path: str | Path,
    output_dir: str | Path,
    llm_quorum_path: str | Path | None = None,
    quality_threshold: float = 0.80,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    result = evaluate_all_gene_candidates_promotion_gate(
        db_path=db_path,
        llm_quorum_path=llm_quorum_path,
        quality_threshold=quality_threshold,
    )
    path = out / "gene_candidate_promotion_audit_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "result": str(path),
        "status": result.status,
        "candidate_count": result.candidate_count,
        "review_ready_count": result.review_ready_count,
        "blockers": result.blockers,
    }

def write_gene_promotion_gate_result(
    *,
    db_path: str | Path,
    gene_id: int,
    output_dir: str | Path,
    claude_evidence_path: str | Path | None = None,
    alternate_evidence_path: str | Path | None = None,
    allow_alternate_when_claude_unavailable: bool = False,
    required_tests_passed: bool = False,
    manifest_updated: bool = False,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    result = evaluate_gene_promotion_gate(
        db_path=db_path,
        gene_id=gene_id,
        claude_evidence_path=claude_evidence_path,
        alternate_evidence_path=alternate_evidence_path,
        allow_alternate_when_claude_unavailable=allow_alternate_when_claude_unavailable,
        required_tests_passed=required_tests_passed,
        manifest_updated=manifest_updated,
    )
    path = out / "gene_promotion_gate_result.json"
    path.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "status": result.status, "blockers": result.blockers}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate read-only GeneDB promotion audit gate.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--gene-id", type=int)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--claude-evidence")
    parser.add_argument("--alternate-evidence")
    parser.add_argument("--allow-alternate-when-claude-unavailable", action="store_true")
    parser.add_argument("--tests-passed", action="store_true")
    parser.add_argument("--manifest-updated", action="store_true")
    parser.add_argument("--all-candidates", action="store_true")
    parser.add_argument("--llm-quorum")
    parser.add_argument("--quality-threshold", type=float, default=0.80)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.all_candidates:
        result = write_all_gene_candidates_promotion_gate_result(
            db_path=args.db,
            output_dir=args.output_dir,
            llm_quorum_path=args.llm_quorum,
            quality_threshold=args.quality_threshold,
        )
    else:
        if args.gene_id is None:
            parser.error("--gene-id is required unless --all-candidates is set")
        result = write_gene_promotion_gate_result(
            db_path=args.db,
            gene_id=args.gene_id,
            output_dir=args.output_dir,
            claude_evidence_path=args.claude_evidence,
            alternate_evidence_path=args.alternate_evidence,
            allow_alternate_when_claude_unavailable=args.allow_alternate_when_claude_unavailable,
            required_tests_passed=args.tests_passed,
            manifest_updated=args.manifest_updated,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
