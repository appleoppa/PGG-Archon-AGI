"""PGG internal HarmRate gate.

Boundary:
- PGG internal risk/negative-utility gate only;
- not an APEX-MOSS verified implementation;
- no zero-risk, no production-safety certification, no AGI/ASI claim;
- no LLM calls, no network, no writes unless caller stores the returned report.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

BOUNDARY = "PGG_internal_HarmRate_gate; APEX_MOSS_VERIFIED=false; no_zero_risk_claim; no_external_safety_certification"
DEFAULT_BLOCK_THRESHOLD = 0.34
DEFAULT_WATCH_THRESHOLD = 0.20
SENSITIVE_TASK_TYPES = {"legal", "production", "security", "credential", "external_public"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def compute_harmrate(task: Mapping[str, Any], *, block_threshold: float = DEFAULT_BLOCK_THRESHOLD, watch_threshold: float = DEFAULT_WATCH_THRESHOLD) -> dict[str, Any]:
    risk = float(task.get("risk", 0.0) or 0.0)
    uncertainty = float(task.get("uncertainty", 0.0) or 0.0)
    source_confidence = float(task.get("source_confidence", 1.0) or 0.0)
    regression_risk = float(task.get("regression_risk", 0.0) or 0.0)
    overclaim_risk = float(task.get("overclaim_risk", 0.0) or 0.0)
    task_type = str(task.get("task_type", "general"))
    external_authority_claim = bool(task.get("external_authority_claim", False))
    apex_moss_claim = bool(task.get("apex_moss_verified_claim", False))

    missing_source_penalty = max(0.0, 1.0 - source_confidence)
    sensitive_multiplier = 1.25 if task_type in SENSITIVE_TASK_TYPES else 1.0
    raw = (0.30 * risk + 0.20 * uncertainty + 0.20 * missing_source_penalty + 0.15 * regression_risk + 0.15 * overclaim_risk) * sensitive_multiplier
    harmrate = max(0.0, min(1.0, raw))

    reasons: list[str] = []
    if external_authority_claim and source_confidence < 0.95:
        reasons.append("external_authority_claim_without_high_source_confidence")
    if apex_moss_claim:
        reasons.append("apex_moss_verified_claim_blocked_until_independent_source")
    if source_confidence < 0.5:
        reasons.append("low_source_confidence")
    if task_type in SENSITIVE_TASK_TYPES:
        reasons.append("sensitive_task_stricter_threshold")

    if apex_moss_claim or (external_authority_claim and source_confidence < 0.95):
        decision = "BLOCK"
    elif harmrate >= block_threshold:
        decision = "BLOCK"
    elif harmrate >= watch_threshold or source_confidence < 0.75:
        decision = "WATCH"
    else:
        decision = "ALLOW"

    return {
        "schema": "PGGInternalHarmRateGate/v1",
        "created_at": _now(),
        "decision": decision,
        "harmrate": round(harmrate, 6),
        "thresholds": {"watch": watch_threshold, "block": block_threshold},
        "reasons": reasons,
        "inputs": {
            "risk": risk,
            "uncertainty": uncertainty,
            "source_confidence": source_confidence,
            "regression_risk": regression_risk,
            "overclaim_risk": overclaim_risk,
            "task_type": task_type,
            "external_authority_claim": external_authority_claim,
            "apex_moss_verified_claim": apex_moss_claim,
        },
        "boundary": BOUNDARY,
        "APEX_MOSS_VERIFIED": False,
        "zero_risk_claim": False,
    }


def write_harmrate_report(report: Mapping[str, Any], output_dir: str | Path) -> str:
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{int(time.time())}_harmrate_gate.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


__all__ = ["BOUNDARY", "compute_harmrate", "write_harmrate_report"]
