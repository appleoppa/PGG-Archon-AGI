"""PGG pull-request merge gate.

Read-only classifier for PR merge recommendations.  It never merges, edits PRs,
or writes credentials/configuration.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

SCHEMA = "pgg-pr-merge-gate/v1"
TIER_AUTO_MERGE = "AUTO_MERGE"
TIER_CANARY = "CANARY"
TIER_HUMAN = "HUMAN"
CANARY_HOURS = 24

_CORE_EXACT = {"config.yaml", "auth.json"}
_CORE_PREFIXES = (
    "agent/route",
    "agent/law",
    "agent/legal",
    "agent/schedul",
)
_CORE_SUBSTRINGS = (
    "credential",
    "security",
)


@dataclass(frozen=True)
class DiffStats:
    """Minimal diff statistics consumed by the merge gate."""

    total_lines: int = 0


def _total_lines(diff_stats: Any) -> int:
    if isinstance(diff_stats, Mapping):
        return int(diff_stats.get("total_lines", 0) or 0)
    return int(getattr(diff_stats, "total_lines", 0) or 0)


def _normalize_path(path: str) -> str:
    # GitHub PR paths are POSIX-style.  Strip common diff prefixes defensively.
    p = str(path or "").strip().replace("\\", "/")
    for prefix in ("a/", "b/", "./"):
        if p.startswith(prefix):
            p = p[len(prefix) :]
    return str(PurePosixPath(p)) if p else ""


def is_core_path(path: str) -> bool:
    """Return True when a file is in a route/legal/scheduler/security/credential lane."""
    p = _normalize_path(path)
    base = PurePosixPath(p).name
    if p in _CORE_EXACT or base in _CORE_EXACT:
        return True
    if any(p.startswith(prefix) for prefix in _CORE_PREFIXES):
        return True
    lowered = p.lower()
    return any(token in lowered for token in _CORE_SUBSTRINGS)


def _ci_green(ci_status: Any) -> bool:
    if isinstance(ci_status, bool):
        return ci_status
    if isinstance(ci_status, Mapping):
        if "green" in ci_status:
            return bool(ci_status["green"])
        ci_status = ci_status.get("status") or ci_status.get("state") or ci_status.get("conclusion")
    status = str(ci_status or "").strip().lower()
    return status in {"green", "pass", "passed", "success", "successful", "ok", "clean"}


def classify_pull_request(
    diff_stats: Any,
    changed_files: Iterable[str],
    ci_status: Any,
    pr_number: int | None = None,
) -> dict[str, Any]:
    """Classify one PR into AUTO_MERGE, CANARY, or HUMAN.

    Rules:
    - core paths always require HUMAN review and should remain draft;
    - <20 changed lines + green CI + non-core => AUTO_MERGE recommendation;
    - <100 changed lines + green CI + non-core => CANARY recommendation;
    - everything else => HUMAN.
    """
    files = [_normalize_path(f) for f in changed_files]
    total = _total_lines(diff_stats)
    core_files = [f for f in files if is_core_path(f)]
    green = _ci_green(ci_status)

    if core_files:
        tier = TIER_HUMAN
        reason = "core_path_changed: " + ", ".join(core_files[:8])
    elif total < 20 and green:
        tier = TIER_AUTO_MERGE
        reason = f"non_core_diff_lt_20_and_ci_green: total_lines={total}"
    elif total < 100 and green:
        tier = TIER_CANARY
        reason = f"non_core_diff_lt_100_and_ci_green: total_lines={total}; require_24h_canary_after_operator_merge"
    else:
        tier = TIER_HUMAN
        if not green:
            reason = f"ci_not_green: ci_status={ci_status!r}; total_lines={total}"
        else:
            reason = f"diff_too_large_for_auto_policy: total_lines={total}"

    return {
        "schema": SCHEMA,
        "pr_number": pr_number,
        "tier": tier,
        "reason": reason,
        "canary_hours": CANARY_HOURS if tier == TIER_CANARY else 0,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify one PR for read-only merge recommendation.")
    parser.add_argument("--pr-number", type=int, default=0)
    parser.add_argument("--total-lines", type=int, default=0)
    parser.add_argument("--ci-status", default="green", help="green/pass/success or non-green value")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file path; repeatable")
    parser.add_argument("--self-test", action="store_true", help="Run built-in sample classifications")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)
    if ns.self_test:
        samples = [
            classify_pull_request(DiffStats(5), ["docs/readme.md"], "green", 1),
            classify_pull_request({"total_lines": 50}, ["agent/helper.py"], "success", 2),
            classify_pull_request(DiffStats(3), ["agent/route_planner.py"], "green", 3),
        ]
        print(json.dumps(samples, ensure_ascii=False, indent=2))
        return 0

    changed = ns.changed_file or ["docs/example.md"]
    result = classify_pull_request(DiffStats(ns.total_lines), changed, ns.ci_status, ns.pr_number or None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
