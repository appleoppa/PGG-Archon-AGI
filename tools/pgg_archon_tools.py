"""PGG Archon read-only tools.

These tools expose PGG Archon scoring surfaces through Hermes Agent's native
ToolRegistry without mutating the core agent loop, provider routing, memory, or
skills.  They are deliberately side-effect-light: callers get JSON reports that
can feed later cron/jobs/quality gates.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from agent.pgg_archon_ultimate_evolution_formula import (
    build_ars_driver_plan,
    build_report_from_runtime_status,
    build_ultimate_evolution_formula_report,
)
from tools.registry import registry


PGG_ULTIMATE_EVOLUTION_SCHEMA: Dict[str, Any] = {
    "name": "pgg_ultimate_evolution",
    "description": (
        "Read-only PGG Archon 终极进化公式 tool. Computes "
        "APEX_AK = Ω_A · EVM_full - ΣΔ_all and optionally returns a GPT-5.5-led "
        "multi-model ARS plan. It never edits files, memory, tools, providers, "
        "or the Hermes core loop."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["score", "ars_plan", "runtime_status", "promotion_status", "evidence_chain_status", "chain_integrity_status"],
                "description": "score=compute formula report; ars_plan=report plus ARS plan; runtime_status=map existing runtime status into formula; promotion_status=read Phase5 promotion gate sidecar status; evidence_chain_status=read Phase7 report/DB/cron evidence-chain status; chain_integrity_status=read Phase8 deterministic integrity manifest gate.",
                "default": "score",
            },
            "omega_a": {
                "type": "number",
                "description": "Optional Ω_A direct value, bounded to [0.5, 2.0]. Prefer measured apex_net/baseline_net when available.",
            },
            "apex_net": {
                "type": "number",
                "description": "Optional measured APEX net score for Ω_A ratio calculation.",
            },
            "baseline_net": {
                "type": "number",
                "description": "Optional measured baseline net score for Ω_A ratio calculation.",
            },
            "evm_signals": {
                "type": "object",
                "description": "0..100 EVM_full sub-signals: task_success, correctness, closure, reasoning_stability, tool_use, long_context_state, self_repair.",
            },
            "delta_signals": {
                "type": "object",
                "description": "0..1 ΣΔ_all severity signals: hallucination, security, unclosed_debt, cost, latency, instability, memory_pollution, tool_risk, governance_debt, critical/p0 flags.",
            },
            "runtime_status": {
                "type": "object",
                "description": "Existing PGG/APEX runtime status dict when action=runtime_status.",
            },
        },
        "additionalProperties": False,
    },
}


def _handle_pgg_ultimate_evolution(args: Dict[str, Any], **_: Any) -> str:
    action = str((args or {}).get("action") or "score")
    if action == "promotion_status":
        from agent.pgg_archon_ultimate_evolution_ars_cycle import build_phase5_promotion_gate

        gate = build_phase5_promotion_gate()
        return json.dumps({
            "promotion_gate": gate,
            "report": {
                "schema": "PGGArchonUltimateEvolutionPromotionStatus/v1",
                "status": gate.get("status"),
                "score": gate.get("score"),
                "decision": gate.get("decision"),
                "blockers": gate.get("blockers"),
                "side_effects": "read_only_status",
                "capability_boundary": "Phase5 sidecar promotion gate status only; not automatic AGI/core promotion.",
            },
        }, ensure_ascii=False, indent=2)
    if action == "evidence_chain_status":
        from agent.pgg_archon_ultimate_evolution_ars_cycle import build_phase7_evidence_chain_status

        chain = build_phase7_evidence_chain_status()
        return json.dumps({
            "evidence_chain": chain,
            "report": {
                "schema": "PGGArchonUltimateEvolutionEvidenceChainStatus/v1",
                "status": chain.get("status"),
                "score": chain.get("score"),
                "decision": chain.get("decision"),
                "blockers": chain.get("blockers"),
                "side_effects": "read_only_status",
                "capability_boundary": "Phase7 sidecar evidence-chain status only; not automatic AGI/core promotion.",
            },
        }, ensure_ascii=False, indent=2)
    if action == "chain_integrity_status":
        from agent.pgg_archon_ultimate_evolution_ars_cycle import build_phase8_chain_integrity_gate

        gate = build_phase8_chain_integrity_gate()
        return json.dumps({
            "chain_integrity": gate,
            "report": {
                "schema": "PGGArchonUltimateEvolutionChainIntegrityStatus/v1",
                "status": gate.get("status"),
                "score": gate.get("score"),
                "decision": gate.get("decision"),
                "manifest_hash": gate.get("manifest_hash"),
                "blockers": gate.get("blockers"),
                "side_effects": "read_only_status",
                "capability_boundary": "Phase8 sidecar integrity manifest only; not automatic AGI/core promotion.",
            },
        }, ensure_ascii=False, indent=2)
    if action == "runtime_status":
        report = build_report_from_runtime_status(args.get("runtime_status") or {})
    else:
        report = build_ultimate_evolution_formula_report(
            evm_signals=args.get("evm_signals") or None,
            delta_signals=args.get("delta_signals") or None,
            omega_a=args.get("omega_a"),
            apex_net=args.get("apex_net"),
            baseline_net=args.get("baseline_net"),
            source="hermes_tool:pgg_ultimate_evolution",
        )
    payload: Dict[str, Any] = {"report": report}
    if action == "ars_plan":
        payload["ars_plan"] = build_ars_driver_plan(report)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _check_pgg_archon_reqs() -> bool:
    return True


registry.register(
    name="pgg_ultimate_evolution",
    toolset="pgg_archon",
    schema=PGG_ULTIMATE_EVOLUTION_SCHEMA,
    handler=_handle_pgg_ultimate_evolution,
    check_fn=_check_pgg_archon_reqs,
    emoji="🧬",
    max_result_size_chars=50_000,
)
