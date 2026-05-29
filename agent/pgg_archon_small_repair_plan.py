"""Bounded repair planner for PGG Archon small bottlenecks.

Converts read-only `small_bottlenecks` signals into explicit, low-risk repair
plans. The planner never executes legal workflow steps, never writes genes, and
never claims AGI completion; it only makes the next safe action auditable.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_PLAN_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/pgg-archon-small-repairs")


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _safe_text(value: Any) -> str:
    return str(value or "")[:300]


def _repair_for_bottleneck(item: Mapping[str, Any], index: int) -> dict[str, Any]:
    source = _safe_text(item.get("source"))
    code = _safe_text(item.get("code") or "UNKNOWN")
    if source == "case_flow_graph_replay":
        next_node = _safe_text(item.get("next_node") or "UNKNOWN")
        return {
            "repair_id": f"pgg_archon_small_repair_{index}_case_flow_{next_node}",
            "source": source,
            "targets": code.split("/") if code else [],
            "priority": "P0" if next_node == "evidence_gate" else "P1",
            "risk": "low",
            "action": "create_evidence_gate_resolution_packet",
            "inputs_required": ["case_id", "evidence_gate_status", "missing_evidence_or_exception_label", "internal_report_status"],
            "completion_standard": "Evidence gate is PASS or a labeled HOLD/BLOCK with internal report; external delivery remains false until PASS.",
            "blocked_side_effects": ["no_external_delivery", "no_case_number_creation", "no_department_call"],
            "next_node": next_node,
            "not_executed": True,
        }
    if source == "eval_regression_harness":
        return {
            "repair_id": f"pgg_archon_small_repair_{index}_eval_p0",
            "source": source,
            "targets": code.split("/") if code else [],
            "priority": "P0",
            "risk": "low",
            "action": "convert_p0_eval_failure_to_expected_red_or_verified_repair_candidate",
            "inputs_required": ["failed_case_id", "assertion_id", "expected", "actual", "bounded_repair_candidate"],
            "completion_standard": "Each P0 eval failure is either expected-red with a stable assertion id or has a bounded repair candidate covered by golden regression.",
            "blocked_side_effects": ["no_gene_write", "no_auto_patch", "no_model_call"],
            "failed_count": item.get("failed_count"),
            "not_executed": True,
        }
    if source == "golden_regression_harness":
        return {
            "repair_id": f"pgg_archon_small_repair_{index}_golden",
            "source": source,
            "targets": code.split("/") if code else [],
            "priority": "P1",
            "risk": "low",
            "action": "repair_golden_expectation_or_diff_bucket",
            "inputs_required": ["case_id", "diff_bucket", "expected", "actual"],
            "completion_standard": "Happy case remains green and negative case remains red with isolated diff bucket.",
            "blocked_side_effects": ["no_core_patch", "no_gene_write"],
            "not_executed": True,
        }
    if source == "autonomy_status":
        return {
            "repair_id": f"pgg_archon_small_repair_{index}_autonomy_mode",
            "source": source,
            "targets": code.split("/") if code else [],
            "priority": "P1",
            "risk": "low",
            "action": "verify_autonomy_warn_state_and_select_dry_run_or_enforce",
            "inputs_required": ["autonomy_mode", "autopromote_enabled", "promotion_count", "stable_ready_count", "pending_rollbacks"],
            "completion_standard": "WARN mode is either intentionally preserved with reason, or moved to DRY_RUN/ENFORCE only after promotion guard is explicit.",
            "blocked_side_effects": ["no_unbounded_autopromotion", "no_core_patch", "no_gene_write"],
            "not_executed": True,
        }
    if source == "promotion_claim_guard":
        return {
            "repair_id": f"pgg_archon_small_repair_{index}_promotion_guard",
            "source": source,
            "targets": code.split("/") if code else [],
            "priority": "P0",
            "risk": "low",
            "action": "resolve_promotion_claim_guard_holds_before_autopromote",
            "inputs_required": ["guard_schema", "allowed", "hold_reasons", "human_ack_status", "gep_actual_execution_status"],
            "completion_standard": "Autopromotion remains blocked until promotion claim guard is present, explicit, and all holds are resolved by the existing gates.",
            "blocked_side_effects": ["no_autopromote", "no_agi_completion_claim", "no_core_patch"],
            "hold_reasons": list(_as_sequence(item.get("hold_reasons")))[:8],
            "not_executed": True,
        }
    if source == "pgg_archon_evidence_loop":
        return {
            "repair_id": f"pgg_archon_small_repair_{index}_evidence_loop",
            "source": source,
            "targets": code.split("/") if code else [],
            "priority": "P1",
            "risk": "low",
            "action": "bind_event_failure_retrospective_metric_evidence",
            "inputs_required": ["event_ledger_status", "failure_sample_status", "task_retrospective_status", "multi_model_ledger_status", "capability_metrics_status"],
            "completion_standard": "Learning-loop evidence is observed or explicitly labeled UNKNOWN/WATCH before any next promotion claim; no raw sensitive content is stored.",
            "blocked_side_effects": ["no_model_call", "no_gene_write", "no_autopromote", "no_sensitive_content_storage"],
            "missing": list(_as_sequence(item.get("missing")))[:8],
            "not_executed": True,
        }
    return {
        "repair_id": f"pgg_archon_small_repair_{index}_manual_review",
        "source": source or "UNKNOWN",
        "targets": code.split("/") if code else [],
        "priority": "P2",
        "risk": "low",
        "action": "manual_small_bottleneck_review",
        "inputs_required": ["source", "code", "action"],
        "completion_standard": "Small bottleneck is converted into a testable low-risk repair case.",
        "blocked_side_effects": ["no_auto_execution"],
        "not_executed": True,
    }


def build_pgg_archon_small_repair_plan(
    runtime_status_surface: Mapping[str, Any],
    *,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_PLAN_DIR,
) -> dict[str, Any]:
    bottlenecks = [dict(item) for item in _as_sequence(runtime_status_surface.get("small_bottlenecks")) if isinstance(item, Mapping)]
    repairs = [_repair_for_bottleneck(item, index) for index, item in enumerate(bottlenecks, 1)]
    p0_count = sum(1 for item in repairs if item.get("priority") == "P0")
    report = {
        "schema": "PGGArchonSmallRepairPlan/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_status": runtime_status_surface.get("status"),
        "source_score": runtime_status_surface.get("score"),
        "bottleneck_count": len(bottlenecks),
        "repair_count": len(repairs),
        "p0_repair_count": p0_count,
        "repairs": repairs,
        "final_recommendation": "execute_low_risk_repair_plan_under_existing_gates" if repairs else "no_small_repair_needed",
        "side_effects": "repair_plan_write" if write_report else "read_only_repair_plan",
        "boundary": "Repair plans are not executed here; legal workflow, gene writes, model calls, and core patches remain blocked.",
        "agi_completion_claim": False,
    }
    report["plan_hash"] = _sha256_obj(report)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_pgg_archon_small_repair_plan.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


build_runtime_small_repair_plan = build_pgg_archon_small_repair_plan

__all__ = ["build_pgg_archon_small_repair_plan", "build_runtime_small_repair_plan"]
