"""Golden regression checks for graph replay + eval harness outputs.

This module implements the low-risk GPT/Claude recommendation from the route
chain review: deterministic golden cases, volatile-field normalization, and
separate diff buckets for graph structure, node order, and eval metrics.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_GOLDEN_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/golden-regressions")
DEFAULT_VOLATILE_FIELDS = {
    "created_at",
    "replay_hash",
    "eval_hash",
    "report_path",
    "replay_path",
    "latency_ms",
    "duration_ms",
}


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _strip_volatile(value: Any, volatile_fields: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _strip_volatile(v, volatile_fields) for k, v in value.items() if str(k) not in volatile_fields}
    if isinstance(value, list):
        return [_strip_volatile(item, volatile_fields) for item in value]
    return value


def normalize_regression_artifact(artifact: Mapping[str, Any], volatile_fields: Sequence[str] | None = None) -> dict[str, Any]:
    fields = set(DEFAULT_VOLATILE_FIELDS)
    if volatile_fields:
        fields.update(str(item) for item in volatile_fields)
    normalized = _strip_volatile(dict(artifact), fields)
    return {
        "schema": "PGGGoldenRegressionNormalizedArtifact/v1",
        "volatile_fields": sorted(fields),
        "artifact": normalized,
        "artifact_hash": hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
    }


def _edge_set(graph: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    edges = graph.get("edges") if isinstance(graph, Mapping) else []
    result: set[tuple[str, str, str]] = set()
    if isinstance(edges, list):
        for edge in edges:
            if isinstance(edge, Mapping):
                result.add((str(edge.get("from")), str(edge.get("to")), str(edge.get("type") or "")))
    return result


def _node_order(graph: Mapping[str, Any]) -> list[str]:
    nodes = graph.get("nodes") if isinstance(graph, Mapping) else []
    if not isinstance(nodes, list):
        return []
    return [str(node.get("node_id")) for node in nodes if isinstance(node, Mapping)]


def _eval_metrics(report: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("status", "case_count", "passed_count", "failed_count", "p0_failed_count", "alert_count", "candidate_count")
    return {key: report.get(key) for key in keys if key in report}


def diff_golden_regression(
    *,
    expected_graph: Mapping[str, Any],
    actual_graph: Mapping[str, Any],
    expected_eval: Mapping[str, Any],
    actual_eval: Mapping[str, Any],
    volatile_fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return separated graph/eval diffs after volatile-field normalization."""
    norm_expected_graph = normalize_regression_artifact(expected_graph, volatile_fields)
    norm_actual_graph = normalize_regression_artifact(actual_graph, volatile_fields)
    norm_expected_eval = normalize_regression_artifact(expected_eval, volatile_fields)
    norm_actual_eval = normalize_regression_artifact(actual_eval, volatile_fields)

    expected_edges = _edge_set(norm_expected_graph["artifact"])
    actual_edges = _edge_set(norm_actual_graph["artifact"])
    expected_order = _node_order(norm_expected_graph["artifact"])
    actual_order = _node_order(norm_actual_graph["artifact"])
    expected_metrics = _eval_metrics(norm_expected_eval["artifact"])
    actual_metrics = _eval_metrics(norm_actual_eval["artifact"])

    graph_structure_diff = {
        "passed": expected_edges == actual_edges,
        "missing_edges": sorted([list(item) for item in expected_edges - actual_edges]),
        "extra_edges": sorted([list(item) for item in actual_edges - expected_edges]),
    }
    node_order_diff = {
        "passed": expected_order == actual_order,
        "expected_order": expected_order if expected_order != actual_order else [],
        "actual_order": actual_order if expected_order != actual_order else [],
    }
    metric_changes = {
        key: {"expected": expected_metrics.get(key), "actual": actual_metrics.get(key)}
        for key in sorted(set(expected_metrics) | set(actual_metrics))
        if expected_metrics.get(key) != actual_metrics.get(key)
    }
    eval_metric_diff = {
        "passed": not metric_changes,
        "changes": metric_changes,
    }
    passed = graph_structure_diff["passed"] and node_order_diff["passed"] and eval_metric_diff["passed"]
    report = {
        "schema": "PGGGoldenRegressionDiff/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "passed": passed,
        "graph_structure_diff": graph_structure_diff,
        "node_order_diff": node_order_diff,
        "eval_metric_diff": eval_metric_diff,
        "normalization": {
            "graph_expected_hash": norm_expected_graph["artifact_hash"],
            "graph_actual_hash": norm_actual_graph["artifact_hash"],
            "eval_expected_hash": norm_expected_eval["artifact_hash"],
            "eval_actual_hash": norm_actual_eval["artifact_hash"],
            "volatile_fields": norm_expected_graph["volatile_fields"],
        },
        "agi_completion_claim": False,
    }
    report["diff_hash"] = _sha256_obj(report)
    return report


def build_golden_regression_report(
    cases: Sequence[Mapping[str, Any]],
    *,
    volatile_fields: Sequence[str] | None = None,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_GOLDEN_DIR,
) -> dict[str, Any]:
    """Evaluate multiple golden regression cases with separated diffs."""
    case_reports: list[dict[str, Any]] = []
    for idx, case in enumerate(cases, 1):
        diff = diff_golden_regression(
            expected_graph=case.get("expected_graph") or {},
            actual_graph=case.get("actual_graph") or {},
            expected_eval=case.get("expected_eval") or {},
            actual_eval=case.get("actual_eval") or {},
            volatile_fields=volatile_fields,
        )
        should_pass = bool(case.get("should_pass", True))
        expectation_met = diff["passed"] is should_pass
        case_reports.append({
            "case_id": str(case.get("case_id") or f"golden_case_{idx}"),
            "name": str(case.get("name") or "golden regression case"),
            "should_pass": should_pass,
            "passed": diff["passed"],
            "expectation_met": expectation_met,
            "diff": diff,
        })
    failed_expectations = [case for case in case_reports if not case["expectation_met"]]
    report = {
        "schema": "PGGGoldenRegressionReport/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "PASS" if not failed_expectations else "BLOCK",
        "case_count": len(case_reports),
        "expectation_met_count": len(case_reports) - len(failed_expectations),
        "failed_expectation_count": len(failed_expectations),
        "cases": case_reports,
        "volatile_fields": sorted(set(DEFAULT_VOLATILE_FIELDS).union(set(str(x) for x in (volatile_fields or [])))),
        "side_effects": "golden_report_write" if write_report else "read_only_golden_regression",
        "boundary": "Deterministic local diff only; no model calls, no gene writes, no legal delivery.",
        "agi_completion_claim": False,
    }
    report["golden_hash"] = _sha256_obj(report)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_golden_regression_report.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


def clone_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    """Small public helper used by tests/smoke scripts to avoid shared mutation."""
    return copy.deepcopy(dict(value))


__all__ = [
    "build_golden_regression_report",
    "clone_artifact",
    "diff_golden_regression",
    "normalize_regression_artifact",
]
