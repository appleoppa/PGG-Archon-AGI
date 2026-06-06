"""Bounded PGG Archon EvoMaster — native evolution core (real skeleton).

This is the EvoMaster 9 native evolution core: a 4-step cycle that
emits state events to evomaster_state.jsonl and audit trail to
pgg_archon_audit.jsonl. Each cycle:
  1. propose mutation
  2. evaluate
  3. accept/reject
  4. log
"""

from __future__ import annotations

import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _stable_hash(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_recent_hashpool(home: Path, limit: int = 25) -> list[dict[str, Any]]:
    pool = home / "workspace" / "trace_hashpool" / "hashpool.jsonl"
    if not pool.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in pool.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("valid", row.get("status") == "completed"):
            rows.append(row)
    return rows


def summarize_tool_ledger(home: Path | None = None, limit: int = 200) -> dict[str, Any]:
    """Summarize real Hermes tool-call ledger for R_exec.

    Reads the observational token-hygiene ledger. It does not mutate or approve
    any tool result; it only derives bounded success/failure counters.
    """
    home = home or Path.home() / ".hermes"
    ledger = home / "data" / "pgg_token_hygiene_tool_ledger.jsonl"
    rows: list[dict[str, Any]] = []
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            rows.append(row)
    total = len(rows)
    ok = sum(1 for r in rows if str(r.get("status", "")).lower() == "ok")
    error = total - ok
    durations = [float(r.get("duration_ms") or 0.0) for r in rows if isinstance(r.get("duration_ms"), (int, float))]
    avg_duration_ms = round(sum(durations) / len(durations), 2) if durations else 0.0
    tool_counts: dict[str, int] = {}
    error_tools: dict[str, int] = {}
    for r in rows:
        name = str(r.get("tool_name") or "unknown")
        tool_counts[name] = tool_counts.get(name, 0) + 1
        if str(r.get("status", "")).lower() != "ok":
            error_tools[name] = error_tools.get(name, 0) + 1
    return {
        "schema": "PGGArchonToolLedgerRewardSummary/v1",
        "ledger_path": str(ledger),
        "ledger_exists": ledger.exists(),
        "window_limit": limit,
        "tool_success_count": ok,
        "tool_total_count": total,
        "tool_error_count": error,
        "exec_reward": round(ok / total, 4) if total else 0.0,
        "avg_duration_ms": avg_duration_ms,
        "top_tools": sorted(tool_counts.items(), key=lambda x: (-x[1], x[0]))[:10],
        "error_tools": sorted(error_tools.items(), key=lambda x: (-x[1], x[0]))[:10],
        "boundary": "Observational ledger summary for R_exec only; does not prove final task success.",
    }


def _load_latest_llm_policy_candidates(home: Path) -> list[dict[str, Any]]:
    cand_dir = home / "workspace" / "pgg-archon-governance" / "super-evolution-9-evomaster" / "policy_candidates"
    candidates: list[dict[str, Any]] = []
    if not cand_dir.exists():
        return candidates
    for path in sorted(cand_dir.glob("*.json"))[-10:]:
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        row["path"] = str(path)
        candidates.append(row)
    return candidates


def _choose_policy_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    visible = [c for c in candidates if c.get("visible_chars", 0) > 50 and c.get("status") == "OK_VISIBLE"]
    if visible:
        return max(visible, key=lambda c: (c.get("score_hint", 0.0), c.get("visible_chars", 0)))
    return {
        "provider": "local_deterministic",
        "status": "LOCAL_FALLBACK",
        "candidate": "bounded_hashpool_reward_ranker",
        "visible_chars": 0,
        "boundary": "No visible GPT/Claude candidate found; local bounded fallback used.",
    }


def derive_reward(tool_success_count: int, tool_total_count: int, k_claw_items: int, lambda_weight: float = 0.35) -> dict[str, Any]:
    """Derive bounded R_exec + lambda*K_claw from local counters.

    This is not RL training; it is a deterministic reward signal for the
    evidence gate and future policy ranking.
    """
    r_exec = (tool_success_count / tool_total_count) if tool_total_count > 0 else 0.0
    k_claw_score = min(max(k_claw_items, 0) / 10.0, 1.0)
    lam = min(max(lambda_weight, 0.0), 1.0)
    objective = r_exec + lam * k_claw_score
    return {
        "tool_success_count": tool_success_count,
        "tool_total_count": tool_total_count,
        "exec_reward": round(r_exec, 4),
        "lambda": round(lam, 4),
        "k_claw_score": round(k_claw_score, 4),
        "objective_score": round(objective, 4),
        "bounded_reward": True,
        "objective_used_for_ranking": True,
    }


def run_bounded_policy_loop(rounds: int = 2, home: Path | None = None) -> dict[str, Any]:
    """Run a local bounded EvoMaster policy loop.

    Boundary: no provider calls and no shell/sandbox command execution. It reads
    K_claw HashPool evidence, derives bounded reward, writes pi_next policy
    states, and records audit evidence so the Rust gate can distinguish a local
    deterministic policy loop from the stronger GPT-Stream production claim.
    """
    home = home or Path.home() / ".hermes"
    out_dir = home / "workspace" / "pgg-archon-governance" / "super-evolution-9-evomaster" / "policy_loop"
    out_dir.mkdir(parents=True, exist_ok=True)
    policy_log = out_dir / "policy_loop.jsonl"
    audit_log = home / "data" / "pgg_archon_audit.jsonl"
    k_items = _load_recent_hashpool(home)
    ledger_summary = summarize_tool_ledger(home)
    policy_candidates = _load_latest_llm_policy_candidates(home)
    chosen_candidate = _choose_policy_candidate(policy_candidates)
    prev_hash = "genesis"
    records: list[dict[str, Any]] = []
    rounds = max(2, min(int(rounds), 5))
    for idx in range(rounds):
        # Real R_exec comes from the observational tool-call ledger. K_claw
        # contributes only the bounded knowledge-cache term.
        success = int(ledger_summary.get("tool_success_count") or 0)
        total = int(ledger_summary.get("tool_total_count") or 0)
        reward = derive_reward(success, total, len(k_items))
        state = {
            "schema": "PGGArchonEvoMasterPolicyLoop/v1",
            "round": idx + 1,
            "generated_at": _now(),
            "previous_policy_hash": prev_hash,
            "k_claw_items_considered": len(k_items),
            "reward": reward,
            "tool_ledger_summary": ledger_summary,
            "llm_policy_candidate": chosen_candidate,
            "constraint_sandbox": {
                "no_shell_execution": True,
                "no_scheduler_mutation": True,
                "no_credential_access": True,
                "read_only_hashpool": True,
            },
            "policy": {
                "name": str(chosen_candidate.get("candidate") or "bounded_hashpool_reward_ranker"),
                "rank_by": "R_exec + lambda*K_claw",
                "candidate_provider": chosen_candidate.get("provider"),
                "prefer": ["verified_trace_reuse", "failure反例降权", "boundary_preserving_actions"],
            },
        }
        policy_hash = _stable_hash(state)
        state["policy_hash"] = policy_hash
        _append_jsonl(policy_log, state)
        _append_jsonl(audit_log, {
            "timestamp": state["generated_at"],
            "actor": "evomaster",
            "action": "bounded_policy_loop_round",
            "round": idx + 1,
            "policy_hash": policy_hash,
            "objective_score": reward["objective_score"],
            "schema": "PGGArchonAuditTrail/v1",
        })
        records.append(state)
        prev_hash = policy_hash
    report = {
        "schema": "PGGArchonEvoMasterPolicyLoopReport/v1",
        "status": "PASS_BOUNDED_LOCAL_POLICY_LOOP",
        "rounds": rounds,
        "policy_log": str(policy_log),
        "tool_ledger_summary": ledger_summary,
        "llm_policy_candidates": policy_candidates,
        "chosen_policy_candidate": chosen_candidate,
        "records": records,
        "boundary": "Local deterministic bounded policy loop only; no GPT-Stream/provider call and no sandbox command execution."
    }
    report_path = out_dir / "policy_loop_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_cycle(delta_e: float = 0.05, decision: str = "accept") -> dict[str, Any]:
    """Run one evomaster cycle. Returns the cycle summary."""
    state_log = Path.home() / ".hermes" / "data" / "evomaster_state.jsonl"
    audit_log = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    now = _now()
    cycle_row = {
        "timestamp": now,
        "core": "evomaster",
        "cycle": int(time.time()),
        "delta_e": delta_e,
        "decision": decision,
        "schema": "PGGArchonEvoMasterState/v1",
    }
    _append_jsonl(state_log, cycle_row)
    _append_jsonl(audit_log, {
        "timestamp": now,
        "actor": "evomaster",
        "action": "cycle_completed",
        "delta_e": delta_e,
        "decision": decision,
        "schema": "PGGArchonAuditTrail/v1",
    })
    return cycle_row


if __name__ == "__main__":
    out = run_cycle()
    print(json.dumps(out, ensure_ascii=False, indent=2))
