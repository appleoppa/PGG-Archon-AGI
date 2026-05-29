"""APEX v3.0 unified evolution score report.

This module turns the AGI unified evolution architecture into an executable,
read-only scoring surface for RuntimeOS.  It does not claim AGI completion and
never mutates genes, skills, memory, or runtime policy.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Mapping


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def _bool(value: Any) -> bool:
    return bool(value)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _score_sensor(status: Mapping[str, Any]) -> Dict[str, Any]:
    quality_gate = _as_mapping(status.get("quality_gate"))
    quality_bundle = _as_mapping(quality_gate.get("evidence_bundle"))
    health = _as_mapping(status.get("health_report"))
    cron = _as_mapping(status.get("cron_dryrun"))
    signals = {
        "quality_gate": _status(quality_gate.get("status")) == "PASS",
        "quality_bundle": bool(quality_bundle.get("valid")),
        "health": _status(health.get("status")) in {"OK", "INFO"},
        "cron_clean": int(cron.get("bad_lines") or 0) == 0,
        "era": bool(status.get("era_report")),
        "co_scientist": bool(status.get("co_scientist_report")),
        "gene_lifecycle": bool(status.get("gene_lifecycle_gate")),
    }
    score = round(100 * sum(1 for ok in signals.values() if ok) / len(signals), 1)
    missing = [key for key, ok in signals.items() if not ok]
    return {"score": score, "signals": signals, "missing": missing}


def _score_diagnosis(status: Mapping[str, Any]) -> Dict[str, Any]:
    gep = _as_mapping(status.get("gep_report"))
    gene_gate = _as_mapping(status.get("gene_lifecycle_gate"))
    quality_gate = _as_mapping(status.get("quality_gate"))
    era = _as_mapping(status.get("era_report"))
    signals = {
        "health_report": bool(status.get("health_report")),
        "quality_missing_evidence_visible": "missing_blocking_evidence" in quality_gate,
        "gene_issues_visible": isinstance(gene_gate.get("issues"), list),
        "gep_warn_visible": _status(gep.get("status")) in {"PASS", "WARN", "BLOCK"},
        "era_path_selected": bool(era.get("selected_path_id")),
    }
    score = round(100 * sum(1 for ok in signals.values() if ok) / len(signals), 1)
    missing = [key for key, ok in signals.items() if not ok]
    return {"score": score, "signals": signals, "missing": missing}


def _score_evolution(status: Mapping[str, Any]) -> Dict[str, Any]:
    co_gene = _as_mapping(status.get("co_scientist_gene_candidate"))
    gene_gate = _as_mapping(status.get("gene_lifecycle_gate"))
    era = _as_mapping(status.get("era_report"))
    co = _as_mapping(status.get("co_scientist_report"))
    gep = _as_mapping(status.get("gep_report"))
    signals = {
        "era_pass": _status(era.get("status")) == "PASS",
        "co_scientist_pass": _status(co.get("status")) == "PASS",
        "gene_candidate_ready": _status(co_gene.get("status")) == "READY",
        "gene_lifecycle_pass": _status(gene_gate.get("status")) == "PASS",
        "gene_not_written": not bool(co_gene.get("gene_library_written")),
        "gep_not_block": _status(gep.get("status")) != "BLOCK",
    }
    score = round(100 * sum(1 for ok in signals.values() if ok) / len(signals), 1)
    missing = [key for key, ok in signals.items() if not ok]
    return {"score": score, "signals": signals, "missing": missing}


def _score_verification(status: Mapping[str, Any]) -> Dict[str, Any]:
    quality = _as_mapping(status.get("quality_gate"))
    formula = _as_mapping(status.get("formula_report"))
    skill = _as_mapping(status.get("skill_registry_policy"))
    signals = {
        "quality_gate_pass": _status(quality.get("status")) == "PASS",
        "formula_pass": _status(formula.get("status")) == "PASS",
        "skill_policy_pass": _status(skill.get("status")) == "PASS",
        "no_pending_rollbacks": int(status.get("pending_rollbacks") or 0) == 0,
        "rollback_gate_present": bool(status.get("promotion_lifecycle_gate")),
    }
    score = round(100 * sum(1 for ok in signals.values() if ok) / len(signals), 1)
    missing = [key for key, ok in signals.items() if not ok]
    return {"score": score, "signals": signals, "missing": missing}


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _score_meta(status: Mapping[str, Any]) -> Dict[str, Any]:
    formula = _as_mapping(status.get("formula_report"))
    cron = _as_mapping(status.get("cron_dryrun"))
    flow = _as_mapping(status.get("flow_reward_report"))
    switch = _as_mapping(status.get("switch_cost_report"))
    meta = _as_mapping(status.get("meta_evolution_report"))
    meta_pass = bool(meta.get("valid")) and _status(meta.get("status")) in {"PASS", "WATCH"}
    meta_signals_raw = meta.get("signals")
    meta_signals = meta_signals_raw if isinstance(meta_signals_raw, Mapping) else {}
    cross_domain = _as_mapping(status.get("cross_domain_core_gene_gate"))
    strategy_ledger_ok = bool(meta_signals.get("strategy_ledger")) or (int(cron.get("unique_keys") or 0) > 0 and int(cron.get("bad_lines") or 0) == 0)
    shadow_replay_ok = bool(meta_signals.get("shadow_replay")) or (bool(flow.get("valid")) and _status(flow.get("status")) in {"PASS", "WATCH"} and bool(flow.get("selected_path_id")))
    drift_sensor_ok = bool(meta_signals.get("drift_sensor")) or (bool(flow.get("valid")) and "score_delta" in flow)
    cost_sensor_ok = bool(meta_signals.get("cost_sensor")) or (bool(switch.get("valid")) and _status(switch.get("status")) in {"PASS", "WATCH", "HOLD"}) or int(cron.get("total_lines") or 0) > 0
    signals = {
        "runtime_reads_itself": status.get("schema") == "ApexRuntimeOSAutonomyStatus/v1",
        "formula_live": bool(formula.get("live_params_used")),
        "era_present": bool(status.get("era_report")),
        "co_scientist_present": bool(status.get("co_scientist_report")),
        "strategy_ledger": strategy_ledger_ok,
        "shadow_replay": shadow_replay_ok,
        "drift_sensor": drift_sensor_ok,
        "cost_sensor": cost_sensor_ok,
        "meta_report_bound": meta_pass,
        "cross_domain_core_genes": _status(cross_domain.get("status")) == "PASS",
    }
    score = round(100 * sum(1 for ok in signals.values() if ok) / len(signals), 1)
    missing = [key for key, ok in signals.items() if not ok]
    return {"score": score, "signals": signals, "missing": missing}


def build_apex_v3_unified_score_report(status: Mapping[str, Any]) -> Dict[str, Any]:
    layers = {
        "sensor": _score_sensor(status),
        "diagnosis": _score_diagnosis(status),
        "evolution": _score_evolution(status),
        "verification": _score_verification(status),
        "meta_evolution": _score_meta(status),
    }
    weights = {"sensor": 0.18, "diagnosis": 0.18, "evolution": 0.22, "verification": 0.24, "meta_evolution": 0.18}
    total = round(sum(layers[name]["score"] * weight for name, weight in weights.items()), 1)
    bottlenecks = sorted(
        [{"layer": name, "score": data["score"], "missing": data["missing"][:6]} for name, data in layers.items()],
        key=lambda item: item["score"],
    )[:3]
    autopromote_enabled = _flag("APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED", "1")
    promotion_enabled = _flag("APEX_RUNTIMEOS_PROMOTION_ENABLED", "1")
    promotion_gate_raw = status.get("promotion_lifecycle_gate")
    promotion_gate = promotion_gate_raw if isinstance(promotion_gate_raw, Mapping) else {}
    gene_gate_raw = status.get("gene_lifecycle_gate")
    gene_gate = gene_gate_raw if isinstance(gene_gate_raw, Mapping) else {}
    quality_gate_raw = status.get("quality_gate")
    quality_gate = quality_gate_raw if isinstance(quality_gate_raw, Mapping) else {}
    promotion_gate_pass = _status(promotion_gate.get("status")) in {"PASS", "BYPASSED"}
    gene_gate_pass = _status(gene_gate.get("status")) == "PASS"
    quality_gate_pass = _status(quality_gate.get("status")) == "PASS"
    gep = _as_mapping(status.get("gep_report"))
    gep_status = _status(gep.get("status"))
    gep_pipeline = _as_mapping(gep.get("safety_pipeline"))
    gep_actual_execution_allowed = bool(gep_pipeline.get("actual_execution_allowed")) and bool(gep_pipeline.get("runtime_allowed"))
    hold_reasons = []
    if gep_status in {"WARN", "BLOCK"}:
        hold_reasons.append("gep_not_fully_pass")
    cross_domain = _as_mapping(status.get("cross_domain_core_gene_gate"))
    if _status(cross_domain.get("status")) != "PASS":
        hold_reasons.append("cross_domain_core_genes_incomplete")
    if layers["meta_evolution"]["score"] < 75:
        hold_reasons.append("meta_evolution_incomplete")
    if layers["verification"]["score"] < 80:
        hold_reasons.append("verification_incomplete")
    recommendations = [
        {"code": "gep_warn_diagnosis", "priority": "P0", "action": "Generate read-only GEP WARN diagnosis and feed it into ERA; do not auto-fix."},
        {"code": "evidence_chain_binding", "priority": "P0", "action": "Require evidence_bundle identity in gene lifecycle decisions before promotion."},
        {"code": "sensor_drift_cost", "priority": "P1", "action": "Add read-only drift and cost sensors for token/latency/regression tracking."},
        {"code": "shadow_replay", "priority": "P1", "action": "Replay candidate genes against historical evidence bundles in shadow mode only."},
        {"code": "strategy_ledger_meta_eval", "priority": "P2", "action": "Append strategy choices and outcomes into a read-only ledger for meta-evolution scoring."},
    ]
    base_report = {
        "schema": "ApexV3UnifiedScoreReport/v1",
        "score": total,
        "weights": weights,
        "layers": layers,
        "bottlenecks": bottlenecks,
        "hold_reasons": hold_reasons,
        "recommendations": recommendations,
        "allows_next_low_risk_cycle": total >= 50,
    }
    from agent.apex_inward_validator import cross_validate_unified_score
    from agent.apex_promotion_claim_guard import evaluate_promotion_claim_guard
    from agent.apex_failure_sample_library import build_failure_sample_library_status
    from agent.apex_multi_model_evidence_ledger import build_multi_model_evidence_ledger
    from agent.apex_real_capability_metrics import build_real_capability_metrics_summary
    from agent.apex_task_retrospective import build_task_retrospective_status

    failure_library_status = build_failure_sample_library_status()
    task_retrospective_status = build_task_retrospective_status()
    multi_model_evidence_ledger = build_multi_model_evidence_ledger()
    case_events = ()
    try:
        from agent.pgg_case_experience_bridge import DEFAULT_EVENTS_DIR
        import json

        events_path = DEFAULT_EVENTS_DIR / "case_events.jsonl"
        if events_path.exists():
            loaded_events = []
            with events_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        parsed = json.loads(line)
                        if isinstance(parsed, dict):
                            loaded_events.append(parsed)
            case_events = tuple(loaded_events)
    except Exception:
        case_events = ()
    try:
        from agent.apex_failure_sample_library import load_failure_samples
        failure_samples = tuple(load_failure_samples())
    except Exception:
        failure_samples = ()
    try:
        from agent.apex_task_retrospective import DEFAULT_RETROSPECTIVE_DIR
        import json

        retrospectives_path = DEFAULT_RETROSPECTIVE_DIR / "retrospectives.jsonl"
        loaded_retrospectives = []
        if retrospectives_path.exists():
            with retrospectives_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        parsed = json.loads(line)
                        if isinstance(parsed, dict):
                            loaded_retrospectives.append(parsed)
        task_retrospectives = tuple(loaded_retrospectives)
    except Exception:
        task_retrospectives = ()
    try:
        from agent.apex_low_risk_autonomy_candidates import generate_autonomy_candidates
        autonomy_candidate_report = generate_autonomy_candidates({
            "failure_samples": failure_samples,
            "real_capability_metrics": {"status": "WATCH"},
        })
        autonomy_candidates = tuple(autonomy_candidate_report.get("candidates", ()))
    except Exception:
        autonomy_candidate_report = {"schema": "ApexLowRiskAutonomyCandidates/v1", "status": "ERROR", "candidate_count": 0, "candidates": ()}
        autonomy_candidates = ()
    real_capability_metrics = build_real_capability_metrics_summary({
        "events": tuple(status.get("events", ())) + case_events,
        "failure_samples": tuple(status.get("failure_samples", ())) + failure_samples,
        "task_retrospectives": tuple(status.get("task_retrospectives", ())) + task_retrospectives,
        "autonomy_candidates": tuple(status.get("autonomy_candidates", ())) + autonomy_candidates,
        "multi_model_ledger": multi_model_evidence_ledger.get("entries", ()),
    })
    try:
        from agent.pgg_archon_status_surface import build_pgg_archon_status_surface
        runtime_status_surface = build_pgg_archon_status_surface()
    except Exception as exc:
        runtime_status_surface = {
            "schema": "PGGArchonStatusSurface/v1",
            "status": "ERROR",
            "score": 0.0,
            "missing": ["runtime_status_surface_error"],
            "error": str(exc)[:200],
            "agi_completion_claim": False,
        }

    inward_validation = cross_validate_unified_score({
        **base_report,
        "allows_autonomous_promotion": False,
    })
    promotion_claim_guard = evaluate_promotion_claim_guard({
        **base_report,
        "allows_autonomous_promotion": False,
    })
    allows_autonomous_promotion = (
        autopromote_enabled
        and promotion_enabled
        and total >= 85
        and layers["meta_evolution"]["score"] >= 75
        and layers["verification"]["score"] >= 80
        and promotion_gate_pass
        and gene_gate_pass
        and quality_gate_pass
        and _status(cross_domain.get("status")) == "PASS"
        and gep_actual_execution_allowed
        and inward_validation.get("cross_validated") is True
        and promotion_claim_guard.get("allowed") is True
        and not hold_reasons
    )
    status_value = "PASS" if total >= 70 and not hold_reasons else ("WATCH" if total >= 50 else "BLOCK")
    return {
        **base_report,
        "status": status_value,
        "allows_autonomous_promotion": allows_autonomous_promotion,
        "inward_validation": inward_validation,
        "promotion_claim_guard": promotion_claim_guard,
        "autonomous_promotion_policy": {
            "autopromote_enabled": autopromote_enabled,
            "promotion_enabled": promotion_enabled,
            "promotion_lifecycle_gate": promotion_gate.get("status"),
            "gene_lifecycle_gate": gene_gate.get("status"),
            "quality_gate": quality_gate.get("status"),
            "gep_actual_execution_allowed": gep_actual_execution_allowed,
            "requires_operator_authorized_enforce_mode": True,
            "requires_dual_inward_validation": True,
            "requires_human_ack": True,
        },
        "agi_completion_claim": False,
        "external_ground_truth_required": True,
        "side_effects": "read_only_report",
        "real_capability_metrics": real_capability_metrics,
        "failure_sample_library": failure_library_status,
        "task_retrospective_status": task_retrospective_status,
        "multi_model_evidence_ledger": multi_model_evidence_ledger,
        "runtime_status_surface": runtime_status_surface,
    }


__all__ = ["build_apex_v3_unified_score_report"]
