"""Read-only PGG PR scanner for merge recommendations.

Scans open PRs on appleoppa/PGG-Archon-AGI via GitHub CLI, classifies each
with agent.pgg_pr_merge_gate, and appends AUTO_MERGE/CANARY recommendations to
a local JSONL ledger.  It never executes a merge and never mutates GitHub state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.pgg_pr_merge_gate import DiffStats, TIER_AUTO_MERGE, TIER_CANARY, classify_pull_request

OWNER_REPO = "appleoppa/PGG-Archon-AGI"
LEDGER = Path.home() / ".hermes/data/pr_merge_ledger.jsonl"
SCAN_DIR = Path.home() / ".hermes/data/pr-scan"
SCAN_LATEST = SCAN_DIR / "latest.json"
RECOMMEND_TIERS = {TIER_AUTO_MERGE, TIER_CANARY}


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str
    stderr: str
    argv: list[str]


def _run_gh(args: list[str], timeout: int = 120) -> CmdResult:
    argv = ["gh", *args]
    try:
        proc = subprocess.run(
            argv,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return CmdResult(127, "", "gh command not found", argv)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "command timed out")
        return CmdResult(124, stdout, stderr, argv)
    return CmdResult(proc.returncode, proc.stdout, proc.stderr, argv)


def _json_or_empty(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return []
    return json.loads(text)


def list_open_prs(repo: str = OWNER_REPO) -> list[dict[str, Any]]:
    # Required base call from task: state open + selected json fields.
    res = _run_gh([
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--json",
        "number,title,headRefName,baseRefName,mergeable,reviews",
    ])
    if res.returncode != 0:
        raise RuntimeError(f"gh pr list failed ({res.returncode}): {res.stderr.strip()}")
    data = _json_or_empty(res.stdout)
    if not isinstance(data, list):
        raise RuntimeError("gh pr list returned non-list JSON")
    return data


def get_changed_files(pr_number: int, repo: str = OWNER_REPO) -> list[str]:
    res = _run_gh(["pr", "diff", str(pr_number), "--repo", repo, "--name-only"])
    if res.returncode == 0:
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]

    # Fallback: parse file headers from a full diff if --name-only is unavailable.
    diff_res = _run_gh(["pr", "diff", str(pr_number), "--repo", repo])
    if diff_res.returncode != 0:
        raise RuntimeError(f"gh pr diff --name-only failed ({res.returncode}): {res.stderr.strip()}")
    files: list[str] = []
    for line in diff_res.stdout.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                path = parts[3]
                if path.startswith("b/"):
                    path = path[2:]
                files.append(path)
    return sorted(set(files))


def get_diff_total_lines(pr_number: int, repo: str = OWNER_REPO) -> int:
    res = _run_gh(["pr", "diff", str(pr_number), "--repo", repo])
    if res.returncode != 0:
        raise RuntimeError(f"gh pr diff failed ({res.returncode}): {res.stderr.strip()}")
    total = 0
    for line in res.stdout.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            total += 1
    return total


def get_ci_status(pr_number: int, repo: str = OWNER_REPO) -> dict[str, Any]:
    """Return a conservative CI status object for the merge gate.

    No status checks configured is not treated as green.  If gh cannot access
    checks, the status is unknown/non-green so the PR falls to HUMAN.
    """
    res = _run_gh(["pr", "checks", str(pr_number), "--repo", repo, "--json", "name,state,bucket"])
    if res.returncode != 0:
        return {"green": False, "status": "unknown", "reason": res.stderr.strip() or "gh pr checks failed"}
    try:
        checks = _json_or_empty(res.stdout)
    except json.JSONDecodeError as exc:
        return {"green": False, "status": "unknown", "reason": f"checks_json_error:{exc}"}
    if not checks:
        return {"green": False, "status": "no_checks", "checks": 0}

    bad: list[str] = []
    pending: list[str] = []
    for check in checks:
        name = str(check.get("name") or "unnamed")
        state = str(check.get("state") or "").upper()
        conclusion = str(check.get("conclusion") or "").upper()
        bucket = str(check.get("bucket") or "").lower()
        if bucket == "pass" or conclusion in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            continue
        if state in {"PENDING", "QUEUED", "IN_PROGRESS", "REQUESTED", "WAITING"} or bucket == "pending":
            pending.append(name)
        else:
            bad.append(name)
    green = not bad and not pending
    return {
        "green": green,
        "status": "green" if green else ("pending" if pending and not bad else "failed"),
        "checks": len(checks),
        "failed": bad[:10],
        "pending": pending[:10],
    }


def _append_recommendation(entry: dict[str, Any], ledger_path: Path = LEDGER) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def scan(repo: str = OWNER_REPO, write_ledger: bool = True) -> dict[str, Any]:
    started = time.time()
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema": "pgg-pr-scan/v1",
        "repo": repo,
        "ts": started,
        "mode": "read_only_recommendations_no_merge",
        "prs": [],
        "recommendations_written": 0,
        "ledger": str(LEDGER),
    }

    try:
        prs = list_open_prs(repo)
    except Exception as exc:
        result.update({"status": "SCAN_ERROR", "error": str(exc)})
        SCAN_LATEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    result["open_pr_count"] = len(prs)
    recommendations = 0
    for pr in prs:
        number = int(pr["number"])
        item: dict[str, Any] = {"pr": pr}
        try:
            changed_files = get_changed_files(number, repo)
            total_lines = get_diff_total_lines(number, repo)
            ci_status = get_ci_status(number, repo)
            gate = classify_pull_request(DiffStats(total_lines), changed_files, ci_status, number)
            item.update({
                "changed_files": changed_files,
                "diff_stats": {"total_lines": total_lines},
                "ci_status": ci_status,
                "classification": gate,
            })
            if gate["tier"] in RECOMMEND_TIERS:
                rec = {
                    "schema": "pgg-pr-merge-recommendation/v1",
                    "ts": time.time(),
                    "repo": repo,
                    "pr_number": number,
                    "title": pr.get("title"),
                    "headRefName": pr.get("headRefName"),
                    "baseRefName": pr.get("baseRefName"),
                    "tier": gate["tier"],
                    "reason": gate["reason"],
                    "canary_hours": gate["canary_hours"],
                    "action": "RECOMMEND_OPERATOR_MERGE_ONLY_NO_AUTOMERGE_EXECUTED",
                }
                item["recommendation"] = rec
                if write_ledger:
                    _append_recommendation(rec)
                    recommendations += 1
        except Exception as exc:
            item.update({
                "classification": {
                    "schema": "pgg-pr-merge-gate/v1",
                    "pr_number": number,
                    "tier": "HUMAN",
                    "reason": f"scan_error: {exc}",
                    "canary_hours": 0,
                },
                "error": str(exc),
            })
        result["prs"].append(item)

    result["recommendations_written"] = recommendations
    result["status"] = "OK"
    result["duration_sec"] = round(time.time() - started, 3)
    SCAN_LATEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan open PRs and write local merge recommendation ledger entries.")
    parser.add_argument("--repo", default=OWNER_REPO)
    parser.add_argument("--no-ledger", action="store_true", help="Scan and print without appending recommendations")
    parser.add_argument("--summary", action="store_true")
    ns = parser.parse_args(argv)

    result = scan(repo=ns.repo, write_ledger=not ns.no_ledger)
    if ns.summary:
        print(json.dumps({
            "schema": result.get("schema"),
            "status": result.get("status"),
            "repo": result.get("repo"),
            "open_pr_count": result.get("open_pr_count", 0),
            "recommendations_written": result.get("recommendations_written", 0),
            "error": result.get("error"),
            "latest": str(SCAN_LATEST),
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    # Return success for launchd even when GitHub auth/network is unavailable; the JSON records the error.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
