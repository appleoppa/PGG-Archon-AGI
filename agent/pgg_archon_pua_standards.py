"""PGG Archon PUA-inspired standards module.

This module codifies behavioral standards from the PUA (Prompt Engineering
Universal Agent) repo into machine-checkable PGG Archon constraints. It does
not add PUA rhetoric, corporate flavors, or emotional escalation — it extracts
the structural patterns that measurably improve agent performance.

Core patterns absorbed:
1. Three Red Lines (三条红线) — close-the-loop, fact-driven, exhaust-everything
2. Proactivity (3.75) — after completing a task, scan for same pattern class
3. Iceberg Rule (冰山法则) — one problem in, one category out
4. Closure evidence — completion requires pastable build/test/curl output
5. Anti-rationalization — unverified attribution is blame-shifting
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_REPORT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/pgg-archon-pua-standards")

# The Three Red Lines — each with a numeric severity for status aggregation
RED_LINES: tuple[dict[str, Any], ...] = (
    {
        "id": "close_the_loop",
        "name": "Close the Loop (闭环)",
        "description": "Claiming completion requires output evidence. No build/test/curl output = no completion.",
        "severity": "P0",
    },
    {
        "id": "fact_driven",
        "name": "Fact-Driven (事实)",
        "description": "Unverified attribution is blame-shifting. Saying 'maybe environment issue' must be verified with tools first.",
        "severity": "P0",
    },
    {
        "id": "exhaust_everything",
        "name": "Exhaust Everything (穷尽)",
        "description": "Saying 'I can't' or 'need more info' before trying all available tools and approaches is a violation.",
        "severity": "P0",
    },
)

# Proactivity standards — what deserves the 3.75 rating vs 3.25
PROACTIVITY_STANDARDS: tuple[dict[str, Any], ...] = (
    {
        "id": "scan_after_fix",
        "name": "Scan module after fix",
        "description": "After fixing one bug, scan the same file/module for the same pattern.",
        "severity": "P1",
    },
    {
        "id": "verify_with_output",
        "name": "Verify with pastable output",
        "description": "Completion must include build/test output pasted in response, not just 'done'.",
        "severity": "P1",
    },
    {
        "id": "search_before_ask",
        "name": "Search before asking user",
        "description": "Exhaust tools before asking the user for information that can be discovered.",
        "severity": "P1",
    },
    {
        "id": "iceberg_one_in_one_category_out",
        "name": "Iceberg Rule (冰山法则)",
        "description": "One problem in, one category out. Fix a bug, check for the pattern everywhere.",
        "severity": "P2",
    },
)

# Behavioral improvement thresholds from PUA benchmark
PUA_BENCHMARK_IMPROVEMENTS = {
    "fix_rate_delta_pct": 36,
    "verification_rate_delta_pct": 65,
    "tool_call_delta_pct": 50,
    "hidden_issue_discovery_delta_pct": 50,
}


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _safe_text(value: Any, limit: int = 300) -> str:
    return str(value or "")[:limit]


def build_pgg_archon_pua_standard_report(
    *,
    red_lines_violated: Sequence[str] | None = None,
    proactivity_violated: Sequence[str] | None = None,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    """Build a machine-checkable PUA standards compliance report.

    Args:
        red_lines_violated: IDs of any red lines currently violated.
        proactivity_violated: IDs of any proactivity standards currently violated.
    """
    violated_red = [str(item) for item in _as_sequence(red_lines_violated or [])]
    violated_pro = [str(item) for item in _as_sequence(proactivity_violated or [])]

    red_line_results: list[dict[str, Any]] = []
    proactivity_results: list[dict[str, Any]] = []

    for line in RED_LINES:
        lid = _safe_text(line["id"])
        ok = lid not in violated_red
        red_line_results.append({
            "standard_id": lid,
            "name": _safe_text(line["name"]),
            "description": _safe_text(line["description"]),
            "severity": _safe_text(line["severity"]),
            "ok": ok,
            "violated": not ok,
        })

    for std in PROACTIVITY_STANDARDS:
        sid = _safe_text(std["id"])
        ok = sid not in violated_pro
        proactivity_results.append({
            "standard_id": sid,
            "name": _safe_text(std["name"]),
            "description": _safe_text(std["description"]),
            "severity": _safe_text(std["severity"]),
            "ok": ok,
            "violated": not ok,
        })

    p0_red_violations = sum(1 for r in red_line_results if not r["ok"] and r["severity"] == "P0")
    total_violations = sum(1 for r in red_line_results if not r["ok"]) + sum(1 for p in proactivity_results if not p["ok"])
    p0_status = "BLOCK" if p0_red_violations > 0 else ("WARN" if total_violations > 0 else "PASS")

    report = {
        "schema": "PGGArchonPUAStandardReport/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "pua_benchmark_improvements": dict(PUA_BENCHMARK_IMPROVEMENTS),
        "standards_count": len(RED_LINES) + len(PROACTIVITY_STANDARDS),
        "red_lines": red_line_results,
        "proactivity_standards": proactivity_results,
        "violated_red_line_ids": [r["standard_id"] for r in red_line_results if not r["ok"]],
        "violated_proactivity_ids": [p["standard_id"] for p in proactivity_results if not p["ok"]],
        "total_violations": total_violations,
        "p0_red_line_violations": p0_red_violations,
        "p0_status": p0_status,
        "side_effects": "read_only_standard_report",
        "boundary": "This report does not modify agent behavior directly; it only surfaces gaps for PGG Archon status to act on.",
        "agi_completion_claim": False,
    }
    report["report_hash"] = _sha256_obj(report)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_pgg_archon_pua_standard_report.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


def build_pgg_archon_task_completion_evidence(
    task_id: str,
    task_summary: str,
    *,
    build_output: str = "",
    test_output: str = "",
    curl_output: str = "",
    verification_method: str = "",
    verification_result: str = "",
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    """Build a task-completion evidence record with pastable output.

    This directly implements the 'Close the Loop' red line: no output evidence
    means no completion.
    """
    evidence = {
        "task_id": _safe_text(task_id, 160) or f"task_{int(time.time())}",
        "task_summary": _safe_text(task_summary, 500),
        "build_output": build_output[:8000] if build_output else "",
        "test_output": test_output[:8000] if test_output else "",
        "curl_output": curl_output[:8000] if curl_output else "",
        "verification_method": _safe_text(verification_method, 300),
        "verification_result": _safe_text(verification_result, 2000),
        "has_closing_evidence": bool(build_output or test_output or curl_output or verification_result),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    evidence["evidence_hash"] = _sha256_obj(evidence)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_{_safe_text(task_id.split('/')[-1].split('.')[0], 60)}_completion_evidence.json"
        out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence["report_path"] = str(out)
    return evidence


__all__ = [
    "build_pgg_archon_pua_standard_report",
    "build_pgg_archon_task_completion_evidence",
]
