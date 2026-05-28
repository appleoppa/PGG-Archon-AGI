"""PGG Archon evidence-gate resolution packet builder.

This module converts a blocked case-flow graph/evidence-gate bottleneck into a
bounded, machine-checkable packet.  It does not open a case, call departments,
read raw case files, create a case number, or allow external legal delivery.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_PACKET_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/pgg-archon-evidence-gate-packets")


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _safe_text(value: Any, limit: int = 300) -> str:
    return str(value or "")[:limit]


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _find_evidence_gate_bottleneck(status_surface: Mapping[str, Any]) -> Mapping[str, Any]:
    for item in _as_sequence(status_surface.get("small_bottlenecks")):
        if isinstance(item, Mapping) and item.get("source") == "case_flow_graph_replay":
            return item
    return {}


def build_pgg_archon_evidence_gate_packet(
    status_surface: Mapping[str, Any],
    *,
    case_id: str = "",
    evidence_gate_status: str = "HOLD",
    missing_evidence_or_exception_label: str = "unresolved_evidence_gate_block",
    internal_report_status: str = "REQUIRED_BEFORE_CLOSE",
    safety_precheck_code: str = "",
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_PACKET_DIR,
) -> dict[str, Any]:
    """Build a bounded evidence-gate resolution packet from status-surface data."""
    bottleneck = _find_evidence_gate_bottleneck(status_surface)
    next_node = _safe_text(bottleneck.get("next_node") or status_surface.get("summary", {}).get("graph_next_node") if isinstance(status_surface.get("summary"), Mapping) else "")
    gate_status = _safe_text(evidence_gate_status).upper() or "HOLD"
    label = _safe_text(missing_evidence_or_exception_label) or "unresolved_evidence_gate_block"
    internal_status = _safe_text(internal_report_status).upper() or "REQUIRED_BEFORE_CLOSE"
    external_delivery_allowed = gate_status == "PASS" and internal_status in {"READY", "NOT_REQUIRED"}

    packet = {
        "schema": "PGGArchonEvidenceGateResolutionPacket/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_status_schema": status_surface.get("schema"),
        "source_status": status_surface.get("status"),
        "source_score": status_surface.get("score"),
        "source_bottleneck_present": bool(bottleneck),
        "source_bottleneck_code": bottleneck.get("code"),
        "next_node": next_node or "UNKNOWN",
        "case_id": _safe_text(case_id, 160),
        "evidence_gate_status": gate_status,
        "missing_evidence_or_exception_label": label,
        "internal_report_status": internal_status,
        "requires_internal_report": gate_status in {"HOLD", "BLOCK", "UNKNOWN", ""},
        "allows_external_delivery": external_delivery_allowed,
        "completion_standard": "Evidence gate is PASS before external delivery; otherwise HOLD/BLOCK must carry an internal report status and explicit missing-evidence/exception label.",
        "blocked_side_effects": [
            "no_external_delivery_unless_evidence_pass",
            "no_case_number_creation",
            "no_department_call",
            "no_gene_write",
            "no_autopromote",
        ],
        "not_executed": True,
        "side_effects": "packet_write" if write_report else "read_only_packet",
        "agi_completion_claim": False,
    }
    # Optional safety precheck using RiskPrediction surface
    if safety_precheck_code:
        try:
            from agent.pgg_archon_p0_surface import scan_content
            scan_result = scan_content(safety_precheck_code, file_path="evidence_gate_precheck")
            packet["safety_precheck"] = {
                "enabled": True,
                "risk_score": scan_result.risk_score,
                "vulnerability_count": len(scan_result.vulnerabilities),
                "vulnerabilities": [{"type": v.vulnerability_type, "severity": v.severity, "line": v.line_number} for v in scan_result.vulnerabilities[:10]],
                "summary": scan_result.to_dict().get("summary", {}),
                "source": "PGGArchonRiskPredictionSurface/v1",
            }
        except Exception as exc:
            packet["safety_precheck"] = {
                "enabled": True,
                "error": f"safety_precheck_failed:{type(exc).__name__}",
                "risk_score": -1,
            }
    else:
        packet["safety_precheck"] = {"enabled": False}
    packet["packet_hash"] = _sha256_obj(packet)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_pgg_archon_evidence_gate_packet.json"
        out.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        packet["report_path"] = str(out)
    return packet


__all__ = ["build_pgg_archon_evidence_gate_packet"]
