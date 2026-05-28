"""PGG Archon status surface for recently unlocked PGG modules.

This read-only surface aggregates module unlock, case-flow graph replay, eval
regression, golden regression, and promotion claim guard reports into a compact
PGG Archon status panel. It does not execute modules, call models, write genes,
or claim AGI completion.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent.apex_runtimeos_autonomy import summarize_autonomy_status
from agent.apex_promotion_claim_guard import evaluate_promotion_claim_guard
from agent.pgg_archon_apex_agi_absorption import build_pgg_archon_apex_agi_absorption_surface
from agent.pgg_archon_evidence_loop_surface import build_pgg_archon_evidence_loop_surface
from agent.pgg_archon_pua_standards import build_pgg_archon_pua_standard_report

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


def build_pgg_archon_status_surface(
    *,
    unlock_report: Mapping[str, Any] | None = None,
    graph_replay_report: Mapping[str, Any] | None = None,
    eval_regression_report: Mapping[str, Any] | None = None,
    golden_regression_report: Mapping[str, Any] | None = None,
    promotion_guard_report: Mapping[str, Any] | None = None,
    evidence_loop_report: Mapping[str, Any] | None = None,
    apex_agi_absorption_report: Mapping[str, Any] | None = None,
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

    signals = {
        "module_unlock_surface": _signal(unlockable_count > 0, unlock, f"unlockable_count={unlockable_count}"),
        "case_flow_graph_replay_present": _signal(bool(graph.get("schema")) and graph_status in {"PASS", "ACTION_REQUIRED", "BLOCK"}, graph, f"replay_status={graph_status}"),
        "eval_regression_present": _signal(bool(eval_report.get("schema")) and eval_status in {"PASS", "WARN", "BLOCK"}, eval_report, f"eval_status={eval_status}"),
        "golden_regression_passed": _signal(golden_status == "PASS" and _as_int(golden.get("failed_expectation_count")) == 0, golden, f"golden_status={golden_status}"),
        "autonomy_mode_ready": _signal(autonomy_mode in {"DRY_RUN", "ENFORCE"}, autonomy, f"autonomy_mode={autonomy_mode}"),
        "promotion_claim_guard_present": _signal(bool(promotion_guard.get("schema")), promotion_guard, f"promotion_guard_allowed={promotion_guard_allowed}"),
        "apex_agi_absorption_surface_ready": _signal(apex_agi_absorption_status == "PASS", apex_agi_absorption, f"apex_agi_absorption_status={apex_agi_absorption_status}"),
        "pua_standards_clean": _signal(pua_p0_status == "PASS" and pua_total_violations == 0, pua_report, f"pua_p0_status={pua_p0_status} violations={pua_total_violations}"),
        "no_external_delivery_from_blocked_graph": _signal(not (graph_status == "BLOCK" and bool(graph.get("allows_external_delivery"))), graph, "blocked_graph_must_not_allow_external_delivery"),
        "no_agi_completion_claims": _signal(
            not any(
                bool(item.get("agi_completion_claim"))
                for item in (unlock, graph, eval_report, golden, autonomy, promotion_guard, evidence_loop, apex_agi_absorption, pua_report)
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
        },
        "autonomy_status": autonomy,
        "promotion_claim_guard": promotion_guard,
        "evidence_loop_surface": evidence_loop,
        "apex_agi_absorption_surface": apex_agi_absorption,
        "pua_standard_report": pua_report,
        "small_bottlenecks": small_bottlenecks,
        "side_effects": "read_only_status_surface",
        "agi_completion_claim": False,
    }


build_apex_runtime_status_surface = build_pgg_archon_status_surface

__all__ = ["build_pgg_archon_status_surface", "build_apex_runtime_status_surface"]

