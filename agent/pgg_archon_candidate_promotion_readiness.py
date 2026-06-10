"""PGG candidate promotion readiness gate.

Boundary:
- aggregates already-produced evidence summaries only;
- no network, no LLM calls, no GeneDB writes;
- does not promote by itself;
- holds candidates when evidence is partial/repro/source-artifact only.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

BOUNDARY = "candidate_promotion_readiness; aggregate gate only; no promotion; no external-source overclaim"
REQUIRED_DOMAINS = (
    "source_evidence",
    "github_closure",
    "engineering_factor",
    "gene_schema",
    "evolution_pattern",
    "harmrate",
)
PROMOTABLE_SOURCE_STATUSES = {"VERIFIED_SOURCE"}
NON_PROMOTABLE_SOURCE_STATUSES = {"PARTIAL_SOURCE", "REPRO_IMPL", "SOURCE_ARTIFACT", "MISSING", "NOISE", "HYPOTHESIS_ONLY"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _get_status(section: Mapping[str, Any]) -> str:
    return str(section.get("status") or section.get("decision") or "").strip()


def evaluate_candidate_promotion_readiness(packet: Mapping[str, Any]) -> dict[str, Any]:
    missing_domains = [name for name in REQUIRED_DOMAINS if name not in packet]
    holds: list[str] = []
    blocks: list[str] = []
    warnings: list[str] = []

    if missing_domains:
        blocks.extend(f"missing_domain:{name}" for name in missing_domains)

    source = packet.get("source_evidence", {}) if isinstance(packet.get("source_evidence", {}), Mapping) else {}
    source_status = str(source.get("source_status") or source.get("status") or "")
    if source_status in NON_PROMOTABLE_SOURCE_STATUSES:
        holds.append(f"source_not_verified:{source_status}")
    elif source_status and source_status not in PROMOTABLE_SOURCE_STATUSES:
        holds.append(f"source_unknown_status:{source_status}")

    github = packet.get("github_closure", {}) if isinstance(packet.get("github_closure", {}), Mapping) else {}
    github_status = str(github.get("status") or "")
    if github_status in NON_PROMOTABLE_SOURCE_STATUSES:
        holds.append(f"github_not_official_verified:{github_status}")
    elif github_status and github_status != "VERIFIED_SOURCE":
        holds.append(f"github_unknown_status:{github_status}")

    engineering = packet.get("engineering_factor", {}) if isinstance(packet.get("engineering_factor", {}), Mapping) else {}
    if engineering.get("valid") is not True:
        blocks.append("engineering_factor_invalid")
    if engineering.get("promotion_allowed") is not True:
        holds.append("engineering_factor_not_promotable")

    schema = packet.get("gene_schema", {}) if isinstance(packet.get("gene_schema", {}), Mapping) else {}
    if schema.get("valid") is not True and schema.get("invalid", 1) != 0:
        blocks.append("gene_schema_invalid")

    evo = packet.get("evolution_pattern", {}) if isinstance(packet.get("evolution_pattern", {}), Mapping) else {}
    evo_status = _get_status(evo)
    if evo_status != "PASS":
        blocks.append(f"evolution_pattern_not_pass:{evo_status or 'missing'}")
    if evo.get("promotion_performed") is True:
        blocks.append("evolution_pattern_gate_must_not_pre_promote")
    if evo.get("official_source_claim") is True:
        blocks.append("official_source_claim_not_allowed_without_verified_source")

    harm = packet.get("harmrate", {}) if isinstance(packet.get("harmrate", {}), Mapping) else {}
    harm_status = _get_status(harm)
    if harm_status in {"BLOCK", "NEED_REVIEW"}:
        blocks.append(f"harmrate_blocks:{harm_status}")
    elif harm_status == "WATCH":
        holds.append("harmrate_watch")
    elif harm_status and harm_status not in {"ALLOW", "PASS"}:
        blocks.append(f"harmrate_unknown_status:{harm_status}")
    if harm.get("APEX_MOSS_VERIFIED") is True:
        blocks.append("apex_moss_verified_claim_not_allowed")
    if harm.get("zero_risk_claim") is True:
        blocks.append("zero_risk_claim_not_allowed")

    if packet.get("manual_reviewer_approved") is not True:
        holds.append("manual_reviewer_approval_missing")
    if packet.get("benchmark_regression_passed") is not True:
        holds.append("benchmark_regression_missing")

    decision = "BLOCK" if blocks else ("HOLD_PATTERN_ONLY" if holds else "READY_FOR_REVIEWED_PROMOTION")
    return {
        "schema": "PGGCandidatePromotionReadiness/v1",
        "created_at": _now(),
        "decision": decision,
        "ready_for_promotion": decision == "READY_FOR_REVIEWED_PROMOTION",
        "holds": holds,
        "blocks": blocks,
        "warnings": warnings,
        "boundary": BOUNDARY,
        "promotion_performed": False,
    }


def evaluate_candidate_promotion_readiness_batch(packets: Sequence[Mapping[str, Any]], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    evaluations = [evaluate_candidate_promotion_readiness(packet) for packet in packets]
    counts: dict[str, int] = {}
    for ev in evaluations:
        counts[ev["decision"]] = counts.get(ev["decision"], 0) + 1
    summary = {
        "schema": "PGGCandidatePromotionReadinessBatch/v1",
        "created_at": _now(),
        "total": len(evaluations),
        "counts": counts,
        "ready_count": counts.get("READY_FOR_REVIEWED_PROMOTION", 0),
        "evaluations": evaluations,
        "boundary": BOUNDARY,
        "promotion_performed": False,
    }
    if output_dir:
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{int(time.time())}_candidate_promotion_readiness.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["output_path"] = str(path)
    return summary


__all__ = ["BOUNDARY", "evaluate_candidate_promotion_readiness", "evaluate_candidate_promotion_readiness_batch"]
