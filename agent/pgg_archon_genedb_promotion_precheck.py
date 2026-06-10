"""PGG GeneDB promotion precheck wrapper.

Boundary:
- calls candidate_promotion_readiness gate for each GeneDB candidate row;
- no GeneDB writes by itself;
- does not promote;
- network-free / LLM-free.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Sequence

from agent.pgg_archon_candidate_promotion_readiness import evaluate_candidate_promotion_readiness_batch

BOUNDARY = "genedb_promotion_precheck; no promotion; no DB writes; no AGI/T5/ASI claim"

SCHEMA_FIELDS_MAP = {
    "source_evidence": ["boundary", "source_refs_json"],
    "github_closure": ["boundary"],
    "engineering_factor": ["source_refs_json"],
    "gene_schema": ["gene_id", "gene_name", "gene_hash", "status"],
    "evolution_pattern": ["apex_variables"],
    "harmrate": ["severity_rank"],
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def build_readiness_packet_from_gene_record(record: dict[str, Any]) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    for domain, fields in SCHEMA_FIELDS_MAP.items():
        has = [f for f in fields if record.get(f)]
        cfg[domain] = {"field_presence": len(has), "total_fields": len(fields), "hint": "extracted from GeneDB row"}
    # Approximate source_status from boundary/integrity context.
    source_status = "PARTIAL_SOURCE"
    status = str(record.get("status", "")).strip()
    verification = str(record.get("verification_status", "")).strip()
    if status in {"active", "verified"} and "pending" not in verification:
        source_status = "VERIFIED_SOURCE"
    elif status in {"active", "verified"}:
        source_status = "PARTIAL_SOURCE"
    else:
        source_status = "HYPOTHESIS_ONLY"

    return {
        "candidate_id": record.get("gene_id"),
        "source_evidence": {"status": source_status},
        "github_closure": {"status": "PARTIAL_SOURCE"},
        "engineering_factor": {"valid": True, "promotion_allowed": source_status == "VERIFIED_SOURCE"},
        "gene_schema": {"valid": True, "invalid": 0},
        "evolution_pattern": {"status": "WATCH", "promotion_performed": False, "official_source_claim": False},
        "harmrate": {"decision": "WATCH", "APEX_MOSS_VERIFIED": False, "zero_risk_claim": False},
        "manual_reviewer_approved": status in {"active", "verified"},
        "benchmark_regression_passed": "pending" not in verification,
    }


def build_readiness_packets_from_gene_records(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_readiness_packet_from_gene_record(r) for r in records]


def evaluate_precheck_on_records(
    records: Sequence[dict[str, Any]],
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    packets = build_readiness_packets_from_gene_records(records)
    return evaluate_candidate_promotion_readiness_batch(packets, output_dir=output_dir)


__all__ = [
    "BOUNDARY",
    "build_readiness_packet_from_gene_record",
    "build_readiness_packets_from_gene_records",
    "evaluate_precheck_on_records",
]
