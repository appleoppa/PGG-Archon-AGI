import json

import model_tools
from tools.registry import discover_builtin_tools, registry


def test_pgg_ultimate_evolution_tool_is_registered_and_dispatchable():
    discover_builtin_tools()
    entry = registry.get_entry("pgg_ultimate_evolution")
    assert entry is not None
    assert entry.toolset == "pgg_archon"
    result = registry.dispatch(
        "pgg_ultimate_evolution",
        {
            "action": "ars_plan",
            "omega_a": 1.1,
            "evm_signals": {
                "task_success": 90,
                "correctness": 85,
                "closure": 80,
                "reasoning_stability": 75,
                "tool_use": 90,
                "long_context_state": 80,
                "self_repair": 80,
            },
            "delta_signals": {"hallucination": 0.05, "security": 0.0},
        },
    )
    payload = json.loads(result)
    assert payload["report"]["formula_name"] == "终极进化公式"
    assert payload["ars_plan"]["primary_model"] == "gpt55_5yuantoken/gpt-5.5"
    assert payload["report"]["side_effects"] == "read_only_report"


def test_pgg_ultimate_evolution_tool_visible_in_toolset():
    discover_builtin_tools()
    from toolsets import resolve_toolset

    assert "pgg_ultimate_evolution" in resolve_toolset("pgg_archon")


def test_pgg_ultimate_evolution_tool_through_model_tools():
    discover_builtin_tools()
    raw = model_tools.handle_function_call(
        "pgg_ultimate_evolution",
        {"action": "score", "omega_a": 1.0},
        skip_pre_tool_call_hook=True,
    )
    payload = json.loads(raw)
    assert payload["report"]["schema"] == "PGGArchonUltimateEvolutionFormulaReport/v1"
    assert payload["report"]["capability_boundary"].startswith("候选评分基因")


def test_pgg_ultimate_evolution_tool_reads_promotion_status():
    discover_builtin_tools()
    raw = registry.dispatch("pgg_ultimate_evolution", {"action": "promotion_status"})
    payload = json.loads(raw)

    assert payload["report"]["schema"] == "PGGArchonUltimateEvolutionPromotionStatus/v1"
    assert payload["report"]["side_effects"] == "read_only_status"
    assert payload["promotion_gate"]["schema"] == "PGGArchonUltimateEvolutionPhase5PromotionGate/v1"


def test_pgg_ultimate_evolution_tool_reads_evidence_chain_status():
    discover_builtin_tools()
    raw = registry.dispatch("pgg_ultimate_evolution", {"action": "evidence_chain_status"})
    payload = json.loads(raw)

    assert payload["report"]["schema"] == "PGGArchonUltimateEvolutionEvidenceChainStatus/v1"
    assert payload["report"]["side_effects"] == "read_only_status"
    assert payload["evidence_chain"]["schema"] == "PGGArchonUltimateEvolutionPhase7EvidenceChainStatus/v1"
