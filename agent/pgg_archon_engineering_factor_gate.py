"""PGG engineering factor gate for absorbed GitHub/material patterns.

Boundary:
- validates engineering-factor cards only;
- no network, no LLM calls, no code import/copy from external repos;
- never promotes GeneDB rows by itself;
- REPRO_IMPL and SOURCE_ARTIFACT are pattern-only, never official-source proof.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

BOUNDARY = "engineering_factor_gate; pattern absorption only; no promotion; no code copy; no official-source claim"
ALLOWED_SOURCE_STATUS = {"VERIFIED_SOURCE", "PARTIAL_SOURCE", "REPRO_IMPL", "SOURCE_ARTIFACT"}
REQUIRED_FIELDS = (
    "id",
    "source_status",
    "source_url",
    "commit_sha",
    "read_scope",
    "source_files",
    "extracted_engineering_factors",
    "pgg_mapping",
    "allowed_use",
    "blocked_claims",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def evaluate_engineering_factor_card(card: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if not card.get(field)]
    errors.extend(f"missing:{field}" for field in missing)

    status = str(card.get("source_status", ""))
    if status and status not in ALLOWED_SOURCE_STATUS:
        errors.append(f"invalid_source_status:{status}")

    factors = card.get("extracted_engineering_factors") or []
    if not isinstance(factors, list) or not factors:
        errors.append("no_engineering_factors")
    else:
        observed = [f for f in factors if isinstance(f, dict) and f.get("observed") is True]
        if not observed:
            errors.append("no_observed_factors")
        for idx, factor in enumerate(factors):
            if not isinstance(factor, dict):
                errors.append(f"factor_not_object:{idx}")
                continue
            if not factor.get("name"):
                errors.append(f"factor_missing_name:{idx}")
            if factor.get("observed") is True and not factor.get("evidence"):
                errors.append(f"observed_factor_missing_evidence:{idx}")

    blocked = card.get("blocked_claims") or []
    if not isinstance(blocked, list) or not blocked:
        errors.append("blocked_claims_required")

    promotion_allowed = status == "VERIFIED_SOURCE" and not errors
    official_source_claim_allowed = status == "VERIFIED_SOURCE" and not errors
    allowed_use = "official-source factor candidate" if official_source_claim_allowed else "pattern-only absorption"
    if status in {"REPRO_IMPL", "SOURCE_ARTIFACT"} and card.get("promote"):
        errors.append("repro_or_artifact_cannot_promote")

    return {
        "schema": "PGGEngineeringFactorCardEvaluation/v1",
        "created_at": _now(),
        "id": card.get("id"),
        "source_status": status,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "promotion_allowed": promotion_allowed,
        "official_source_claim_allowed": official_source_claim_allowed,
        "allowed_use": allowed_use,
        "boundary": BOUNDARY,
    }


def evaluate_engineering_factor_cards(cards: Sequence[Mapping[str, Any]], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    evaluations = [evaluate_engineering_factor_card(card) for card in cards]
    counts: dict[str, int] = {}
    for ev in evaluations:
        counts[ev["source_status"]] = counts.get(ev["source_status"], 0) + 1
    summary = {
        "schema": "PGGEngineeringFactorGate/v1",
        "created_at": _now(),
        "boundary": BOUNDARY,
        "total": len(evaluations),
        "valid": sum(1 for ev in evaluations if ev["valid"]),
        "invalid": sum(1 for ev in evaluations if not ev["valid"]),
        "promotion_allowed_count": sum(1 for ev in evaluations if ev["promotion_allowed"]),
        "official_source_claim_allowed_count": sum(1 for ev in evaluations if ev["official_source_claim_allowed"]),
        "source_status_counts": counts,
        "evaluations": evaluations,
    }
    if output_dir:
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{int(time.time())}_engineering_factor_gate.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["output_path"] = str(path)
    return summary


__all__ = ["BOUNDARY", "evaluate_engineering_factor_card", "evaluate_engineering_factor_cards"]
