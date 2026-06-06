from __future__ import annotations

from agent.pgg_archon_evomaster import (
    build_evomaster_gate_input,
    probe_evomaster,
    run_rust_evomaster_gate,
    write_version_marker,
)


def test_evomaster_python_wrapper_calls_rust_gate() -> None:
    result = run_rust_evomaster_gate()
    assert result["schema"] == "HermesPGGEvoMasterGate/v1"
    assert "rust_module_version" in result
    assert result["status"] in {
        "PASS_BOUNDED_EVOMASTER_CORE_EVIDENCE_GATE",
        "PARTIAL_HASHPOOL_AND_STATUS_GATE_POLICY_LOOP_WATCH",
        "WATCH_PARTIAL_SURFACES_ONLY",
        "BLOCKED_INSUFFICIENT_EVIDENCE",
    }
    assert "full AGI" in result["boundary"]


def test_evomaster_current_evidence_reads_policy_loop_when_present() -> None:
    evidence = build_evomaster_gate_input()
    assert evidence["source"]["rust_gate_integrated"] is True
    assert evidence["policy"]["pi_next_written"] is True
    assert evidence["policy"]["core_reads_k_claw"] is True
    assert evidence["policy"]["loop_rounds"] >= 2
    assert evidence["reward"]["tool_total_count"] > 0
    assert evidence["reward"]["objective_used_for_ranking"] is True


def test_evomaster_version_marker_makes_status_surface_active() -> None:
    write_version_marker("0.1.0-test")
    probe = probe_evomaster()
    assert probe.probes["version_marker_present"] == "present"
    assert probe.status == "ACTIVE"
