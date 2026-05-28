from __future__ import annotations

from pathlib import Path

from agent.pgg_archon_evidence_gate_packet import build_pgg_archon_evidence_gate_packet


def _status_surface():
    return {
        "schema": "PGGArchonStatusSurface/v1",
        "status": "WATCH",
        "score": 87.5,
        "summary": {"graph_next_node": "evidence_gate"},
        "small_bottlenecks": [
            {
                "code": "Agt/Pan",
                "source": "case_flow_graph_replay",
                "next_node": "evidence_gate",
                "action": "resolve_or_label_next_blocking_case_flow_node",
                "risk": "low",
            }
        ],
    }


def test_evidence_gate_packet_defaults_to_hold_without_external_delivery():
    packet = build_pgg_archon_evidence_gate_packet(_status_surface())

    assert packet["schema"] == "PGGArchonEvidenceGateResolutionPacket/v1"
    assert packet["source_bottleneck_present"] is True
    assert packet["next_node"] == "evidence_gate"
    assert packet["evidence_gate_status"] == "HOLD"
    assert packet["requires_internal_report"] is True
    assert packet["allows_external_delivery"] is False
    assert "no_external_delivery_unless_evidence_pass" in packet["blocked_side_effects"]
    assert packet["not_executed"] is True
    assert packet["agi_completion_claim"] is False
    assert packet["side_effects"] == "read_only_packet"
    assert packet["packet_hash"]


def test_evidence_gate_packet_can_write_bounded_report(tmp_path):
    packet = build_pgg_archon_evidence_gate_packet(
        _status_surface(),
        case_id="PGG-CIV-20260528-001",
        evidence_gate_status="BLOCK",
        missing_evidence_or_exception_label="missing_contract_original",
        internal_report_status="DRAFTED",
        write_report=True,
        report_dir=tmp_path,
    )

    assert packet["case_id"] == "PGG-CIV-20260528-001"
    assert packet["evidence_gate_status"] == "BLOCK"
    assert packet["missing_evidence_or_exception_label"] == "missing_contract_original"
    assert packet["internal_report_status"] == "DRAFTED"
    assert packet["allows_external_delivery"] is False
    assert Path(packet["report_path"]).exists()


def test_evidence_gate_packet_only_allows_external_delivery_on_pass_and_ready_internal_state():
    packet = build_pgg_archon_evidence_gate_packet(
        _status_surface(),
        evidence_gate_status="PASS",
        missing_evidence_or_exception_label="resolved",
        internal_report_status="READY",
    )

    assert packet["requires_internal_report"] is False
    assert packet["allows_external_delivery"] is True
    assert packet["not_executed"] is True


def test_evidence_gate_safety_precheck_skipped_by_default():
    """When safety_precheck_code is empty, safety_precheck is disabled."""
    packet = build_pgg_archon_evidence_gate_packet(_status_surface())
    assert packet["safety_precheck"]["enabled"] is False


def test_evidence_gate_safety_precheck_detects_risk():
    """When safety_precheck_code contains a vulnerability, risk_score > 0."""
    risky_code = 'cursor.execute(f"SELECT * FROM users WHERE id = {uid}")'
    packet = build_pgg_archon_evidence_gate_packet(
        _status_surface(),
        safety_precheck_code=risky_code,
    )
    assert packet["safety_precheck"]["enabled"] is True
    assert packet["safety_precheck"]["risk_score"] > 0
    assert packet["safety_precheck"]["vulnerability_count"] >= 1
    assert any("SQL Injection" in v["type"] for v in packet["safety_precheck"]["vulnerabilities"])


def test_evidence_gate_safety_precheck_passes_clean_code():
    """Clean code should have risk_score == 0."""
    clean_code = "def hello(): return 'world'"
    packet = build_pgg_archon_evidence_gate_packet(
        _status_surface(),
        safety_precheck_code=clean_code,
    )
    assert packet["safety_precheck"]["enabled"] is True
    assert packet["safety_precheck"]["risk_score"] == 0
    assert packet["safety_precheck"]["vulnerability_count"] == 0
