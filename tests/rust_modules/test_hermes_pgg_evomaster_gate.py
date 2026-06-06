from __future__ import annotations

import json


def test_evomaster_gate_sample_passes() -> None:
    import hermes_pgg_evomaster_gate as gate

    evidence = json.loads(gate.sample_input_json())
    decision = json.loads(gate.evaluate_evidence_json(json.dumps(evidence)))

    assert "Super Evolution 9" in gate.version()
    assert decision["schema"] == "HermesPGGEvoMasterGate/v1"
    assert decision["status"] == "PASS_BOUNDED_EVOMASTER_CORE_EVIDENCE_GATE"
    assert decision["score"] >= 0.9
    assert decision["gaps"] == []
    assert "full AGI" in decision["boundary"]


def test_evomaster_gate_current_partial_does_not_overclaim() -> None:
    import hermes_pgg_evomaster_gate as gate

    partial = json.loads(gate.sample_input_json())
    partial["reward"].update(
        {
            "tool_success_count": 0,
            "tool_total_count": 0,
            "exec_reward": 0.0,
            "lambda": 0.0,
            "k_claw_score": 0.0,
            "objective_score": 0.0,
            "bounded_reward": False,
            "objective_used_for_ranking": False,
        }
    )
    partial["policy"].update(
        {
            "pi_next_written": False,
            "pi_next_differs_from_previous": False,
            "core_reads_k_claw": False,
            "sandbox_execution_evidence": False,
            "loop_rounds": 0,
        }
    )
    decision = json.loads(gate.evaluate_evidence_json(json.dumps(partial)))

    assert decision["status"] != "PASS_BOUNDED_EVOMASTER_CORE_EVIDENCE_GATE"
    assert any("reward_objective_gate_low" in gap for gap in decision["gaps"])
    assert any("policy_update_loop_gate_low" in gap for gap in decision["gaps"])
