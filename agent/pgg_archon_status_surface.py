"""PGG Archon status surface for recently unlocked PGG modules.

This read-only surface aggregates module unlock, case-flow graph replay, eval
regression, golden regression, and promotion claim guard reports into a compact
PGG Archon status panel. It does not execute modules, call models, write genes,
or claim AGI completion.

Expanded (2026-05-28): ERA, Flow Reward, Switch-cost, GPO, Co-Scientist, and
Quality Evidence Bundle read-only status lookups wired into signals, bottlenecks,
and summary fields. All lookups use load_latest_* or build_*_report functions
that are themselves read-only and stateless.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.apex_runtimeos_autonomy import summarize_autonomy_status
from agent.apex_promotion_claim_guard import evaluate_promotion_claim_guard
from agent.pgg_archon_apex_agi_absorption import build_pgg_archon_apex_agi_absorption_surface
from agent.pgg_archon_diagnostic_surface import build_pgg_archon_diagnostic_surface
from agent.pgg_archon_evidence_loop_surface import build_pgg_archon_evidence_loop_surface
from agent.pgg_archon_pua_standards import build_pgg_archon_pua_standard_report
from agent.pgg_archon_p0_surface import build_pgg_archon_p0_surface
from agent.pgg_archon_quality_gate_surface import build_pgg_archon_quality_gate_surface
from agent.pgg_archon_research_extraction_surface import build_pgg_archon_research_extraction_surface
from agent.apex_co_scientist import load_latest_debate_report, load_latest_gene_candidate
from agent.apex_era import load_latest_era_report
from agent.apex_flow_reward import load_latest_flow_reward_report
from agent.apex_switch_cost import load_latest_switch_cost_report
from agent.apex_gpo import build_gpo_report
from runtime.quality.evidence_bundle import load_latest_quality_evidence_bundle

DEFAULT_UNLOCK_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/apex-module-unlocks")
DEFAULT_GRAPH_REPLAY_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/case-flow-graph-replays")
DEFAULT_EVAL_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/eval-regression-harness")
DEFAULT_GOLDEN_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/golden-regressions")


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def _latest_json(directory: str | Path, pattern: str) -> dict[str, Any]:
    root = Path(directory)
    if not root.exists():
        return {}
    files = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["_source_path"] = str(path)
                return data
        except Exception:
            continue
    return {}


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _signal(ok: bool, source: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "reason": reason,
        "source_schema": source.get("schema"),
        "source_path": source.get("_source_path"),
    }


def _build_promotion_readiness(
    *,
    surface_status: str,
    score: float,
    missing: Sequence[str],
    graph_status: str,
    promotion_guard_allowed: bool,
    promotion_guard_holds: Sequence[str],
    small_bottlenecks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive a read-only promotion readiness gate from the status surface.

    The status score measures whether observability inputs are present. Promotion
    readiness is stricter: a green surface still must not imply autonomous
    promotion while human acknowledgements, blocked case-flow nodes, or other
    bounded repair bottlenecks remain.
    """
    blocker_codes = [str(item.get("code") or "UNKNOWN") for item in small_bottlenecks]
    human_gate_codes = {
        str(item.get("code") or "UNKNOWN")
        for item in small_bottlenecks
        if str(item.get("code") or "") in {"Agt/Pan", "Aut/Guard"}
    }
    human_ack_pending = (not promotion_guard_allowed) or "human_ack_required" in set(str(item) for item in promotion_guard_holds)
    safety_missing = [name for name in missing if name in {"no_external_delivery_from_blocked_graph", "no_agi_completion_claims"}]

    if human_ack_pending:
        readiness_status = "HUMAN_ACK_REQUIRED"
    elif safety_missing:
        readiness_status = "BLOCKED_BY_SAFETY_GATE"
    elif graph_status == "BLOCK":
        readiness_status = "BLOCKED_BY_CASE_FLOW_GATE"
    elif small_bottlenecks:
        readiness_status = "BOUNDED_REPAIR_REQUIRED"
    elif surface_status == "PASS" and score >= 90.0 and graph_status == "PASS" and promotion_guard_allowed:
        readiness_status = "READY_FOR_HUMAN_REVIEW"
    else:
        readiness_status = "NOT_READY"

    return {
        "schema": "PGGArchonPromotionReadiness/v1",
        "status": readiness_status,
        "allows_autonomous_promotion": False,
        "requires_human_ack": True,
        "human_ack_pending": bool(human_ack_pending or human_gate_codes),
        "blocker_codes": blocker_codes,
        "human_gate_codes": sorted(human_gate_codes),
        "safety_missing": safety_missing,
        "promotion_guard_allowed": bool(promotion_guard_allowed),
        "reason": "read_only_gate_no_auto_promotion_no_agi_completion_claim",
        "agi_completion_claim": False,
    }


def build_pgg_archon_status_surface(
    *,
    unlock_report: Mapping[str, Any] | None = None,
    graph_replay_report: Mapping[str, Any] | None = None,
    eval_regression_report: Mapping[str, Any] | None = None,
    golden_regression_report: Mapping[str, Any] | None = None,
    promotion_guard_report: Mapping[str, Any] | None = None,
    evidence_loop_report: Mapping[str, Any] | None = None,
    apex_agi_absorption_report: Mapping[str, Any] | None = None,
    p0_surface_report: Mapping[str, Any] | None = None,
    quality_gate_report: Mapping[str, Any] | None = None,
    research_extraction_report: Mapping[str, Any] | None = None,
    unlock_dir: str | Path = DEFAULT_UNLOCK_DIR,
    graph_replay_dir: str | Path = DEFAULT_GRAPH_REPLAY_DIR,
    eval_dir: str | Path = DEFAULT_EVAL_DIR,
    golden_dir: str | Path = DEFAULT_GOLDEN_DIR,
) -> dict[str, Any]:
    """Build a compact status panel from latest structured reports."""
    unlock = dict(unlock_report) if unlock_report is not None else dict(_latest_json(unlock_dir, "*apex_module_unlock_registry.json"))
    graph = dict(graph_replay_report) if graph_replay_report is not None else dict(_latest_json(graph_replay_dir, "*case_flow_graph_replay.json"))
    eval_report = dict(eval_regression_report) if eval_regression_report is not None else dict(_latest_json(eval_dir, "*eval_regression_harness.json"))
    golden = dict(golden_regression_report) if golden_regression_report is not None else dict(_latest_json(golden_dir, "*golden_regression_report.json"))
    try:
        autonomy = dict(summarize_autonomy_status())
    except Exception:
        autonomy = {}

    unlockable_count = _as_int(unlock.get("unlockable_count") or unlock.get("module_count"))
    graph_status = _status(graph.get("replay_status"))
    eval_status = _status(eval_report.get("status"))
    golden_status = _status(golden.get("status"))
    autonomy_mode = _status(autonomy.get("mode"))
    autopromote_enabled = bool(autonomy.get("autopromote_enabled"))
    promotion_count = _as_int(autonomy.get("promotion_count"))
    stable_ready_count = _as_int(autonomy.get("stable_ready_count"))
    pending_rollbacks = _as_int(autonomy.get("pending_rollbacks"))

    guard_snapshot = {
        "schema": "PGGArchonStatusSurfaceSnapshot/v1",
        "score": 100.0,
        "hold_reasons": [],
        "agi_completion_claim": False,
        "allows_autonomous_promotion": autopromote_enabled,
        "autonomous_promotion_policy": {
            "gep_actual_execution_allowed": bool(autonomy.get("gep_actual_execution_allowed")),
        },
    }
    try:
        promotion_guard = dict(promotion_guard_report) if promotion_guard_report is not None else dict(evaluate_promotion_claim_guard(guard_snapshot))
    except Exception as exc:
        promotion_guard = {"schema": None, "allowed": False, "hold_reasons": [f"promotion_guard_unavailable:{type(exc).__name__}"]}
    promotion_guard_allowed = bool(promotion_guard.get("allowed"))
    promotion_guard_holds = [str(item) for item in promotion_guard.get("hold_reasons", [])[:8]] if isinstance(promotion_guard.get("hold_reasons"), list) else []
    try:
        evidence_loop = dict(evidence_loop_report) if evidence_loop_report is not None else dict(build_pgg_archon_evidence_loop_surface())
    except Exception as exc:
        evidence_loop = {"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "ERROR", "missing": [f"evidence_loop_unavailable:{type(exc).__name__}"], "agi_completion_claim": False}
    evidence_loop_status = _status(evidence_loop.get("status"))
    evidence_loop_missing = [str(item) for item in evidence_loop.get("missing", [])[:8]] if isinstance(evidence_loop.get("missing"), list) else []
    try:
        apex_agi_absorption = dict(apex_agi_absorption_report) if apex_agi_absorption_report is not None else dict(build_pgg_archon_apex_agi_absorption_surface())
    except Exception as exc:
        apex_agi_absorption = {"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "ERROR", "blocking_failures": [f"apex_agi_absorption_unavailable:{type(exc).__name__}"], "agi_completion_claim": False}
    apex_agi_absorption_status = _status(apex_agi_absorption.get("status"))
    apex_agi_absorption_blocking = [
        str(item.get("gate_name") if isinstance(item, Mapping) else item)
        for item in _as_sequence(apex_agi_absorption.get("blocking_failures"))[:8]
    ]
    try:
        pua_report = dict(build_pgg_archon_pua_standard_report())
    except Exception as exc:
        pua_report = {"schema": "PGGArchonPUAStandardReport/v1", "p0_status": "ERROR", "total_violations": 0, "agi_completion_claim": False}
    pua_p0_status = _status(pua_report.get("p0_status"))
    pua_total_violations = _as_int(pua_report.get("total_violations"))
    try:
        p0_surface = dict(p0_surface_report) if p0_surface_report is not None else dict(build_pgg_archon_p0_surface())
    except Exception as exc:
        p0_surface = {"schema": "PGGArchonP0Surface/v1", "status": "ERROR", "aggregate": {"blocking_failures": [f"p0_surface_unavailable:{type(exc).__name__}"], "surfaces_ok": 0, "surfaces_total": 3, "no_smoke_failures": False}, "agi_completion_claim": False}
    p0_surface_status = _status(p0_surface.get("status"))
    p0_surface_blocking = [
        str(item) for item in _as_sequence(p0_surface.get("aggregate", {}).get("blocking_failures"))[:8]
    ]
    p0_surfaces_ok = _as_int(p0_surface.get("aggregate", {}).get("surfaces_ok"))
    p0_surfaces_total = _as_int(p0_surface.get("aggregate", {}).get("surfaces_total"))
    try:
        quality_gate = dict(quality_gate_report) if quality_gate_report is not None else dict(build_pgg_archon_quality_gate_surface())
    except Exception as exc:
        quality_gate = {"schema": "PGGArchonQualityGateSurface/v1", "status": "ERROR", "blocking_failures": [f"quality_gate_unavailable:{type(exc).__name__}"], "warning_failures": [], "agi_completion_claim": False}
    quality_gate_status = _status(quality_gate.get("status"))
    quality_gate_schema_ok = quality_gate.get("schema") == "PGGArchonQualityGateSurface/v1"
    quality_gate_blocking = [str(item) for item in _as_sequence(quality_gate.get("blocking_failures"))[:8]]
    quality_gate_warnings = [str(item) for item in _as_sequence(quality_gate.get("warning_failures"))[:8]]
    try:
        research_extraction = dict(research_extraction_report) if research_extraction_report is not None else dict(build_pgg_archon_research_extraction_surface())
    except Exception as exc:
        research_extraction = {"schema": "PGGArchonResearchExtractionSurface/v1", "status": "ERROR", "warnings": [f"research_extraction_unavailable:{type(exc).__name__}"], "agi_completion_claim": False}
    research_extraction_status = _status(research_extraction.get("status"))
    research_extraction_schema_ok = research_extraction.get("schema") == "PGGArchonResearchExtractionSurface/v1"
    research_extraction_warnings = [str(item) for item in _as_sequence(research_extraction.get("warnings"))[:8]]

    # --- Read-only lookups for standalone APEX modules ---
    def _safe_load(fn, empty=None):
        try:
            val = fn()
            if val is not None:
                return dict(val)
        except Exception:
            pass
        return empty if empty is not None else {}
    era_report = _safe_load(load_latest_era_report)
    era_status = _status(era_report.get("status"))
    flow_report = _safe_load(load_latest_flow_reward_report)
    flow_status = _status(flow_report.get("status"))
    switch_report = _safe_load(load_latest_switch_cost_report)
    switch_status = _status(switch_report.get("status"))
    co_debate = _safe_load(load_latest_debate_report)
    co_debate_status = _status(co_debate.get("status"))
    co_gene = _safe_load(load_latest_gene_candidate)
    co_gene_status = _status(co_gene.get("status"))
    gpo_report = _safe_load(build_gpo_report)
    gpo_status = _status(gpo_report.get("status"))
    quality_ev = _safe_load(load_latest_quality_evidence_bundle)
    quality_ev_valid = bool(quality_ev.get("schema"))

    # Diagnostic surface: aggregate already-collected sub-surface statuses into
    # a unified subsystem-health view. Pure read-only — no IO, no model calls.
    def _diag_status(value: str) -> str:
        v = (value or "").upper()
        if v == "PASS":
            return "healthy"
        if v in {"BLOCK", "ERROR", "UNKNOWN"}:
            return "critical"
        return "degraded"

    diagnostic_subsystems = [
        {"name": "evidence_loop", "status": _diag_status(evidence_loop_status), "details": f"missing={len(evidence_loop_missing)}"},
        {"name": "apex_agi_absorption", "status": _diag_status(apex_agi_absorption_status), "details": f"blocking={len(apex_agi_absorption_blocking)}"},
        {"name": "pua_standards", "status": _diag_status(pua_p0_status), "details": f"violations={pua_total_violations}"},
        {"name": "p0_surface", "status": _diag_status(p0_surface_status), "details": f"ok={p0_surfaces_ok}/{p0_surfaces_total}"},
        {"name": "quality_gate", "status": _diag_status(quality_gate_status), "details": f"blocking={len(quality_gate_blocking)} warnings={len(quality_gate_warnings)}"},
        {"name": "research_extraction", "status": _diag_status(research_extraction_status), "details": f"warnings={len(research_extraction_warnings)}"},
        {"name": "case_flow_graph_replay", "status": _diag_status(graph_status), "details": f"next_node={graph.get('next_node')}"},
        {"name": "eval_regression", "status": _diag_status(eval_status), "details": f"failed_count={eval_report.get('failed_count')}"},
        {"name": "golden_regression", "status": _diag_status(golden_status), "details": f"failed_expectation_count={golden.get('failed_expectation_count')}"},
        {"name": "era", "status": _diag_status(era_status), "details": ""},
        {"name": "flow_reward", "status": _diag_status(flow_status), "details": ""},
        {"name": "switch_cost", "status": "degraded" if switch_status == "HOLD" else _diag_status(switch_status), "details": ""},
        {"name": "co_scientist_debate", "status": _diag_status(co_debate_status), "details": ""},
        {"name": "co_scientist_gene", "status": "healthy" if co_gene_status in {"READY", "PASS"} else _diag_status(co_gene_status), "details": ""},
        {"name": "gpo", "status": "healthy" if gpo_status in {"PASS", "WATCH"} else _diag_status(gpo_status), "details": ""},
        {"name": "quality_evidence_bundle", "status": "healthy" if quality_ev_valid else "degraded", "details": f"valid={quality_ev_valid}"},
    ]
    try:
        diagnostic_surface = build_pgg_archon_diagnostic_surface(diagnostic_subsystems)
    except Exception as exc:
        diagnostic_surface = {
            "schema": "PGGArchonDiagnosticSurface/v1",
            "status": "ERROR",
            "overall_status": "ERROR",
            "subsystems": [],
            "warnings": [f"diagnostic_surface_unavailable:{type(exc).__name__}"],
            "agi_completion_claim": False,
        }
    diagnostic_overall = _status(diagnostic_surface.get("overall_status"))

    # --- Aggregate signals ---
    signals = {
        "module_unlock_surface": _signal(unlockable_count > 0, unlock, f"unlockable_count={unlockable_count}"),
        "case_flow_graph_replay_present": _signal(bool(graph.get("schema")) and graph_status in {"PASS", "ACTION_REQUIRED", "BLOCK"}, graph, f"replay_status={graph_status}"),
        "eval_regression_present": _signal(bool(eval_report.get("schema")) and eval_status in {"PASS", "WARN", "BLOCK"}, eval_report, f"eval_status={eval_status}"),
        "golden_regression_passed": _signal(golden_status == "PASS" and _as_int(golden.get("failed_expectation_count")) == 0, golden, f"golden_status={golden_status}"),
        "autonomy_mode_ready": _signal(autonomy_mode in {"DRY_RUN", "ENFORCE"}, autonomy, f"autonomy_mode={autonomy_mode}"),
        "promotion_claim_guard_present": _signal(bool(promotion_guard.get("schema")), promotion_guard, f"promotion_guard_allowed={promotion_guard_allowed}"),
        "apex_agi_absorption_surface_ready": _signal(apex_agi_absorption_status == "PASS", apex_agi_absorption, f"apex_agi_absorption_status={apex_agi_absorption_status}"),
        "pua_standards_clean": _signal(pua_p0_status == "PASS" and pua_total_violations == 0, pua_report, f"pua_p0_status={pua_p0_status} violations={pua_total_violations}"),
        "p0_surfaces_ready": _signal(
            p0_surface_status == "PASS" and p0_surfaces_ok == p0_surfaces_total,
            p0_surface,
            f"p0_surface_status={p0_surface_status} ok={p0_surfaces_ok}/{p0_surfaces_total}",
        ),
        "quality_gate_surface_ready": _signal(
            quality_gate_schema_ok and quality_gate_status in {"PASS", "WATCH"},
            quality_gate,
            f"quality_gate_status={quality_gate_status} blocking={len(quality_gate_blocking)} warnings={len(quality_gate_warnings)}",
        ),
        "research_extraction_surface_ready": _signal(
            research_extraction_schema_ok and research_extraction_status in {"PASS", "WATCH"},
            research_extraction,
            f"research_extraction_status={research_extraction_status} warnings={len(research_extraction_warnings)}",
        ),
        "era_report_present": _signal(era_status == "PASS", era_report, f"era_status={era_status}"),
        "flow_reward_report_present": _signal(flow_status == "PASS", flow_report, f"flow_status={flow_status}"),
        "switch_cost_report_present": _signal(switch_status in {"PASS", "HOLD"}, switch_report, f"switch_status={switch_status}"),
        "co_scientist_debate_present": _signal(co_debate_status == "PASS", co_debate, f"co_debate_status={co_debate_status}"),
        "co_scientist_gene_candidate_ready": _signal(co_gene_status in {"READY", "PASS"}, co_gene, f"co_gene_status={co_gene_status}"),
        "gpo_report_present": _signal(gpo_status in {"PASS", "WATCH"}, gpo_report, f"gpo_status={gpo_status}"),
        "quality_evidence_bundle_valid": _signal(quality_ev_valid, quality_ev, f"evidence_valid={quality_ev_valid}"),
        "no_external_delivery_from_blocked_graph": _signal(not (graph_status == "BLOCK" and bool(graph.get("allows_external_delivery"))), graph, "blocked_graph_must_not_allow_external_delivery"),
        "no_agi_completion_claims": _signal(
            not any(
                bool(item.get("agi_completion_claim"))
                for item in (unlock, graph, eval_report, golden, autonomy, promotion_guard,
                            evidence_loop, apex_agi_absorption, pua_report, p0_surface, quality_gate,
                            research_extraction, era_report, flow_report, switch_report, co_debate, co_gene,
                            gpo_report, quality_ev)
            ),
            {},
            "all_pgg_archon_status_inputs_keep_agi_completion_claim_false",
        ),
    }
    ok_count = sum(1 for item in signals.values() if item["ok"])
    score = round(100 * ok_count / len(signals), 1)
    missing = [name for name, item in signals.items() if not item["ok"]]
    status = "PASS" if score >= 90 and not missing else ("WATCH" if score >= 60 else "BLOCK")
    small_bottlenecks: list[dict[str, Any]] = []
    if graph_status == "BLOCK":
        small_bottlenecks.append({
            "code": "Agt/Pan",
            "source": "case_flow_graph_replay",
            "next_node": graph.get("next_node"),
            "action": "resolve_or_label_next_blocking_case_flow_node",
            "risk": "low",
        })
    if eval_status == "BLOCK":
        small_bottlenecks.append({
            "code": "Err/Res",
            "source": "eval_regression_harness",
            "failed_count": eval_report.get("failed_count"),
            "action": "verify_p0_alerts_or_convert_to_bounded_repair_cases",
            "risk": "low",
        })
    if golden_status != "PASS":
        small_bottlenecks.append({
            "code": "Clw/Log",
            "source": "golden_regression_harness",
            "failed_expectation_count": golden.get("failed_expectation_count"),
            "action": "repair_golden_regression_expectation_or_diff_bucket",
            "risk": "low",
        })
    if autonomy_mode == "WARN":
        small_bottlenecks.append({
            "code": "Aut/Wrn",
            "source": "autonomy_status",
            "mode": autonomy_mode,
            "promotion_count": promotion_count,
            "stable_ready_count": stable_ready_count,
            "pending_rollbacks": pending_rollbacks,
            "action": "review_autopromote_mode_and_clear_warn_state_if_intended",
            "risk": "low",
        })
    if autopromote_enabled and not promotion_guard_allowed:
        small_bottlenecks.append({
            "code": "Aut/Guard",
            "source": "promotion_claim_guard",
            "hold_reasons": promotion_guard_holds,
            "action": "clear_promotion_claim_guard_holds_before_autopromote",
            "risk": "low",
        })
    if evidence_loop_status in {"UNKNOWN", "WATCH", "ERROR"}:
        small_bottlenecks.append({
            "code": "Evd/Loop",
            "source": "pgg_archon_evidence_loop",
            "status": evidence_loop_status,
            "missing": evidence_loop_missing,
            "action": "bind_learning_loop_evidence_before_next_promotion_claim",
            "risk": "low",
        })
    if apex_agi_absorption_status != "PASS":
        small_bottlenecks.append({
            "code": "Abs/APEX",
            "source": "pgg_archon_apex_agi_absorption",
            "status": apex_agi_absorption_status,
            "blocking_failures": apex_agi_absorption_blocking,
            "action": "resolve_apex_agi_absorption_gates_before_runtime_import",
            "risk": "low",
        })
    if pua_p0_status in {"BLOCK", "ERROR", "UNKNOWN"}:
        small_bottlenecks.append({
            "code": "PUA/Red",
            "source": "pgg_archon_pua_standards",
            "p0_status": pua_p0_status,
            "total_violations": pua_total_violations,
            "action": "resolve_pua_red_line_or_standard_violations_before_promotion",
            "risk": "low",
        })
    if p0_surface_status != "PASS":
        small_bottlenecks.append({
            "code": "P0/Srf",
            "source": "pgg_archon_p0_surface",
            "status": p0_surface_status,
            "surfaces_ok": p0_surfaces_ok,
            "surfaces_total": p0_surfaces_total,
            "blocking_failures": p0_surface_blocking,
            "action": "resolve_p0_surface_smoke_failures_before_promotion",
            "risk": "low",
        })
    if not quality_gate_schema_ok:
        small_bottlenecks.append({
            "code": "QG/Schema",
            "source": "pgg_archon_quality_gate_surface",
            "status": quality_gate_status,
            "action": "reject_or_rebuild_malformed_quality_gate_report",
            "risk": "low",
        })
    elif quality_gate_status == "BLOCK":
        small_bottlenecks.append({
            "code": "QG/Block",
            "source": "pgg_archon_quality_gate_surface",
            "status": quality_gate_status,
            "blocking_failures": quality_gate_blocking,
            "warning_failures": quality_gate_warnings,
            "action": "supply_or_fix_quality_gate_evidence_before_promotion",
            "risk": "low",
        })
    elif quality_gate_status in {"WATCH", "ERROR", "UNKNOWN"}:
        small_bottlenecks.append({
            "code": "QG/Watch",
            "source": "pgg_archon_quality_gate_surface",
            "status": quality_gate_status,
            "blocking_failures": quality_gate_blocking,
            "warning_failures": quality_gate_warnings,
            "action": "review_quality_gate_warning_evidence_before_promotion_claim",
            "risk": "low",
        })
    if not research_extraction_schema_ok:
        small_bottlenecks.append({
            "code": "Res/Schema",
            "source": "pgg_archon_research_extraction_surface",
            "status": research_extraction_status,
            "action": "reject_or_rebuild_malformed_research_extraction_report",
            "risk": "low",
        })
    elif research_extraction_status in {"ERROR", "UNKNOWN"}:
        small_bottlenecks.append({
            "code": "Res/Error",
            "source": "pgg_archon_research_extraction_surface",
            "status": research_extraction_status,
            "warnings": research_extraction_warnings,
            "action": "repair_research_extraction_surface_before_material_absorption",
            "risk": "low",
        })
    elif research_extraction_status == "WATCH" and "ResearchTopicMissing" not in research_extraction_warnings and "ResearchSourcesMissing" not in research_extraction_warnings:
        small_bottlenecks.append({
            "code": "Res/Watch",
            "source": "pgg_archon_research_extraction_surface",
            "status": research_extraction_status,
            "warnings": research_extraction_warnings,
            "action": "review_research_extraction_relevance_before_material_absorption",
            "risk": "low",
        })
    if era_status not in {"PASS", ""}:
        small_bottlenecks.append({
            "code": "ERA/Warn",
            "source": "apex_era",
            "era_status": era_status,
            "action": "review_era_path_search_or_bootstrap_latest_report",
            "risk": "low",
        })
    if flow_status not in {"PASS", ""}:
        small_bottlenecks.append({
            "code": "Flow/Warn",
            "source": "apex_flow_reward",
            "flow_status": flow_status,
            "action": "review_flow_reward_report_or_bootstrap_latest_report",
            "risk": "low",
        })
    if switch_status not in {"PASS", "HOLD", ""}:
        small_bottlenecks.append({
            "code": "Swi/Warn",
            "source": "apex_switch_cost",
            "switch_status": switch_status,
            "action": "review_switch_cost_report_or_bootstrap_latest_report",
            "risk": "low",
        })
    if co_debate_status not in {"PASS", ""} or co_gene_status not in {"READY", "PASS", ""}:
        small_bottlenecks.append({
            "code": "CoS/Warn",
            "source": "apex_co_scientist",
            "debate_status": co_debate_status,
            "gene_status": co_gene_status,
            "action": "review_co_scientist_debate_or_gene_candidate_or_bootstrap",
            "risk": "low",
        })
    if gpo_status not in {"PASS", "WATCH", ""}:
        small_bottlenecks.append({
            "code": "GPO/Warn",
            "source": "apex_gpo",
            "gpo_status": gpo_status,
            "action": "review_gpo_report_or_rerun_static_scan",
            "risk": "low",
        })
    if not quality_ev_valid:
        small_bottlenecks.append({
            "code": "QEv/Warn",
            "source": "quality_evidence_bundle",
            "valid": quality_ev_valid,
            "action": "generate_or_update_quality_evidence_bundle",
            "risk": "low",
        })

    promotion_readiness = _build_promotion_readiness(
        surface_status=status,
        score=score,
        missing=missing,
        graph_status=graph_status,
        promotion_guard_allowed=promotion_guard_allowed,
        promotion_guard_holds=promotion_guard_holds,
        small_bottlenecks=small_bottlenecks,
    )

    return {
        "schema": "PGGArchonStatusSurface/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "score": score,
        "signals": signals,
        "missing": missing,
        "latest_sources": {
            "unlock_report": unlock.get("_source_path"),
            "graph_replay_report": graph.get("_source_path"),
            "eval_regression_report": eval_report.get("_source_path"),
            "golden_regression_report": golden.get("_source_path"),
        },
        "summary": {
            "unlockable_count": unlockable_count,
            "graph_replay_status": graph_status,
            "graph_next_node": graph.get("next_node"),
            "eval_status": eval_status,
            "eval_failed_count": eval_report.get("failed_count"),
            "golden_status": golden_status,
            "golden_failed_expectation_count": golden.get("failed_expectation_count"),
            "autonomy_mode": autonomy_mode,
            "autopromote_enabled": autopromote_enabled,
            "promotion_count": promotion_count,
            "stable_ready_count": stable_ready_count,
            "pending_rollbacks": pending_rollbacks,
            "promotion_guard_allowed": promotion_guard_allowed,
            "promotion_guard_hold_reasons": promotion_guard_holds,
            "evidence_loop_status": evidence_loop_status,
            "evidence_loop_missing": evidence_loop_missing,
            "apex_agi_absorption_status": apex_agi_absorption_status,
            "apex_agi_absorption_ready_candidate_count": apex_agi_absorption.get("ready_candidate_count"),
            "apex_agi_absorption_blocking_failures": apex_agi_absorption_blocking,
            "pua_p0_status": pua_p0_status,
            "pua_total_violations": pua_total_violations,
            "quality_gate_status": quality_gate_status,
            "quality_gate_schema_ok": quality_gate_schema_ok,
            "quality_gate_blocking_failures": quality_gate_blocking,
            "quality_gate_warning_failures": quality_gate_warnings,
            "research_extraction_status": research_extraction_status,
            "research_extraction_schema_ok": research_extraction_schema_ok,
            "research_extraction_warnings": research_extraction_warnings,
            "research_extraction_key_point_count": research_extraction.get("key_point_count"),
            "research_extraction_relevance": research_extraction.get("relevance"),
            "era_status": era_status,
            "flow_status": flow_status,
            "switch_status": switch_status,
            "co_debate_status": co_debate_status,
            "co_gene_status": co_gene_status,
            "gpo_status": gpo_status,
            "quality_evidence_valid": quality_ev_valid,
            "promotion_readiness_status": promotion_readiness["status"],
            "promotion_requires_human_ack": promotion_readiness["requires_human_ack"],
            "promotion_human_ack_pending": promotion_readiness["human_ack_pending"],
            "diagnostic_overall_status": diagnostic_overall,
            "diagnostic_critical_count": diagnostic_surface.get("critical_count", 0),
            "diagnostic_degraded_count": diagnostic_surface.get("degraded_count", 0),
            "diagnostic_healthy_count": diagnostic_surface.get("healthy_count", 0),
        },
        "autonomy_status": autonomy,
        "promotion_claim_guard": promotion_guard,
        "evidence_loop_surface": evidence_loop,
        "apex_agi_absorption_surface": apex_agi_absorption,
        "pua_standard_report": pua_report,
        "era_report": era_report,
        "flow_reward_report": flow_report,
        "switch_cost_report": switch_report,
        "co_scientist_debate": co_debate,
        "co_scientist_gene_candidate": co_gene,
        "gpo_report": gpo_report,
        "quality_evidence_bundle": quality_ev,
        "promotion_readiness": promotion_readiness,
        "diagnostic_surface": diagnostic_surface,
        "small_bottlenecks": small_bottlenecks,
        "side_effects": "read_only_status_surface",
        "agi_completion_claim": False,
    }


build_apex_runtime_status_surface = build_pgg_archon_status_surface

__all__ = ["build_pgg_archon_status_surface", "build_apex_runtime_status_surface"]
