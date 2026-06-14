"""PGG Archon source evidence gate for evolution-route candidates.

Boundary:
- no network access inside this gate; it evaluates provided evidence cards only;
- no LLM calls, no provider/config/scheduler/security mutation;
- never promotes a candidate gene by itself;
- classifies evidence as VERIFIED_SOURCE / PARTIAL_SOURCE / MISSING_SOURCE /
  HYPOTHESIS_ONLY so downstream promotion cannot confuse names with proof.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

REQUIRED_FIELDS = ("candidate", "claim", "source_title", "source_url", "source_type", "evidence_note")
HYPOTHESIS_TERMS = ("意识", "consciousness", "量子", "quantum", "ASI", "APEX_MAX", "L5")
DEFAULT_OUTPUT_DIR = Path("/Users/appleoppa/.hermes/workspace/pgg-archon-governance/source-evidence-cards")
BOUNDARY = (
    "source evidence gate only classifies provided evidence; no network, no LLM, "
    "no promotion, no AGI/T5/ASI claim"
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _hash_card(card: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(card, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def classify_evidence_card(card: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if not str(card.get(field, "")).strip()]
    claim_text = " ".join(str(card.get(k, "")) for k in ("candidate", "claim", "evidence_note"))
    hypothesis_flag = any(term.lower() in claim_text.lower() for term in HYPOTHESIS_TERMS)
    source_url = str(card.get("source_url", "")).strip()
    source_type = str(card.get("source_type", "")).strip().lower()
    has_verifiable_url = source_url.startswith(("http://", "https://", "file://"))
    source_type_ok = source_type in {
        "paper",
        "github",
        "github_repro",
        "github_candidate",
        "github_source_artifact",
        "official_doc",
        "local_file",
        "uploaded_note",
        "unknown_unverified",
    }
    promotion_source_types = {"paper", "github", "official_doc", "local_file"}
    partial_only_source_types = {"unknown_unverified", "uploaded_note", "github_repro", "github_candidate", "github_source_artifact"}

    if hypothesis_flag and not has_verifiable_url:
        status = "HYPOTHESIS_ONLY"
    elif missing:
        status = "MISSING_SOURCE"
    elif not has_verifiable_url or not source_type_ok:
        status = "PARTIAL_SOURCE"
    elif source_type in partial_only_source_types:
        # Uploaded notes, GitHub reproductions/candidates, and preserved external
        # source artifacts prove that material exists, not that the repo is the
        # official paper source or that PGG has validated the capability.
        status = "PARTIAL_SOURCE"
    else:
        status = "VERIFIED_SOURCE"

    promotion_allowed = status == "VERIFIED_SOURCE" and source_type in promotion_source_types and not hypothesis_flag
    return {
        "schema": "PGGSourceEvidenceCardEvaluation/v1",
        "created_at": _now(),
        "candidate": card.get("candidate"),
        "status": status,
        "promotion_allowed": promotion_allowed,
        "missing_fields": missing,
        "hypothesis_flag": hypothesis_flag,
        "source_url": source_url,
        "source_type": source_type,
        "boundary": BOUNDARY,
        "card_hash": _hash_card(card),
    }


def evaluate_evidence_cards(cards: Sequence[Mapping[str, Any]], *, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    evaluations = [classify_evidence_card(card) for card in cards]
    counts: dict[str, int] = {}
    for ev in evaluations:
        counts[ev["status"]] = counts.get(ev["status"], 0) + 1
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": "PGGSourceEvidenceGate/v1",
        "created_at": _now(),
        "boundary": BOUNDARY,
        "total": len(evaluations),
        "counts": counts,
        "promotion_allowed_count": sum(1 for ev in evaluations if ev["promotion_allowed"]),
        "evaluations": evaluations,
    }
    path = out_dir / f"{int(time.time())}_source_evidence_gate.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["output_path"] = str(path)
    return summary


__all__ = [
    "BOUNDARY",
    "DEFAULT_OUTPUT_DIR",
    "REQUIRED_FIELDS",
    "classify_evidence_card",
    "evaluate_evidence_cards",
]
