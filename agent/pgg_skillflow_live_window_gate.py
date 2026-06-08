"""PGG SkillFlow live-window gate with strict/mechanical separation.

Restored lightweight gate: ledger-backed, read-only for status; appends exactly one
observation only when --task/--evidence are supplied.
"""
from __future__ import annotations

import argparse, hashlib, json, time
from pathlib import Path
from typing import Any

HOME = Path.home()
DATA = HOME / ".hermes" / "data"
LEDGER = DATA / "pgg_skillflow_live_observation_ledger.jsonl"
STATUS = DATA / "pgg_skillflow_live_window_status.json"
MIN_INITIAL = 50
MIN_STABLE = 100
BOUNDARY = "Anti-fabrication live-window gate: strict live observations exclude bulk/read-only harvesting; no route enforcement, no answer-chain replacement."
RAW_BLOCK = ("raw_oss_to_100", "continuous_oss_to_100")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"_parse_error": True, "raw": line})
    return rows


def _strict_ok(row: dict[str, Any]) -> bool:
    evidence = str(row.get("evidence") or "")
    return bool(
        row.get("kind") == "real_live"
        and row.get("outcome") == "PASS"
        and row.get("adopted") is True
        and row.get("strict_counts_toward_live_window") is True
        and row.get("evidence_class") == "task_level_evidence"
        and row.get("granularity") == "task"
        and evidence.startswith(str(HOME / ".hermes"))
        and not any(x in evidence for x in RAW_BLOCK)
    )


def compute_status() -> dict[str, Any]:
    rows = _load_jsonl(LEDGER)
    strict = sum(1 for r in rows if _strict_ok(r))
    mech = sum(1 for r in rows if r.get("kind") == "real_live" and r.get("outcome") == "PASS" and r.get("adopted") is True)
    bulk = sum(1 for r in rows if any(x in str(r.get("evidence") or "") for x in RAW_BLOCK))
    weak = sum(1 for r in rows if r.get("kind") == "real_live" and r.get("outcome") == "PASS" and r.get("adopted") is True and not _strict_ok(r) and not any(x in str(r.get("evidence") or "") for x in RAW_BLOCK))
    collapse = sum(1 for r in rows if r.get("collapse_risk"))
    unsafe = sum(1 for r in rows if r.get("production_answer_chain_replaced") or r.get("route_enforce"))
    status = "PASS_STABLE_LIVE_WINDOW" if strict >= MIN_STABLE else ("PASS_INITIAL_LIVE_WINDOW" if strict >= MIN_INITIAL else "BLOCKED_INITIAL_LIVE_WINDOW")
    out = {
        "schema": "PGGSkillFlowLiveWindowStatus/v2",
        "status": status,
        "real_live_count": strict,
        "strict_real_live": strict,
        "mechanical_live_count": mech,
        "bulk_oss_excluded_count": bulk,
        "weak_or_wrong_evidence_excluded_count": weak,
        "non_live_excluded_count": max(0, len(rows) - mech),
        "minimum_initial": MIN_INITIAL,
        "minimum_stable": MIN_STABLE,
        "remaining_to_initial": max(0, MIN_INITIAL - strict),
        "remaining_to_stable": max(0, MIN_STABLE - strict),
        "collapse_risk_count": collapse,
        "unsafe_enforcement_count": unsafe,
        "ledger": str(LEDGER),
        "production_answer_chain_replaced": False,
        "route_enforce": False,
        "boundary": BOUNDARY,
    }
    out["summary_zh"] = f"SE19 live窗口门禁：{status}；strict_real_live {strict}/50初始、{strict}/100稳定；mechanical={mech}；bulk排除 {bulk}；弱证据排除 {weak}；坍塌 {collapse}；unsafe_enforcement {unsafe}；production_answer_chain_replaced=false；route_enforce=false。"
    return out


def write_status() -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    out = compute_status()
    STATUS.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def append_observation(args: argparse.Namespace) -> dict[str, Any]:
    ev = Path(args.evidence).expanduser()
    if not ev.is_absolute() or not ev.exists():
        raise SystemExit(f"evidence_missing_or_not_absolute: {ev}")
    evs = str(ev)
    if any(x in evs for x in RAW_BLOCK):
        raise SystemExit("raw_or_continuous_oss_single_repo_evidence_forbidden")
    obs_id = "live:" + hashlib.sha256(f"{time.time()}|{args.task}|{evs}".encode()).hexdigest()[:16]
    row = {
        "schema": "PGGSkillFlowLiveObservation/v2",
        "ts": time.time(),
        "observation_id": obs_id,
        "kind": args.kind,
        "counts_toward_live_window": args.kind == "real_live" and args.outcome == "PASS" and args.adopted,
        "strict_counts_toward_live_window": args.kind == "real_live" and args.outcome == "PASS" and args.adopted,
        "evidence_class": "task_level_evidence",
        "granularity": "task",
        "classification_reason": "task_level_real_live_with_evidence",
        "task_text": args.task,
        "task_class": "gate_validation",
        "risk_flags": [],
        "selected_advisory_route": "skillflow_advisor_primary",
        "collapse_risk": False,
        "adopted": args.adopted,
        "outcome": args.outcome,
        "evidence": evs,
        "production_answer_chain_replaced": False,
        "route_enforce": False,
        "boundary": BOUNDARY,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--task")
    ap.add_argument("--kind", default="real_live")
    ap.add_argument("--outcome", default="PASS")
    ap.add_argument("--adopted", type=lambda x: str(x).lower() in {"1","true","yes"}, default=True)
    ap.add_argument("--evidence")
    args = ap.parse_args()
    appended = None
    if args.task:
        if not args.evidence:
            raise SystemExit("--evidence required with --task")
        appended = append_observation(args)
    status = write_status()
    if appended:
        status = {"appended_observation": appended, "status": status}
    print(json.dumps(status, ensure_ascii=False, indent=2 if args.summary else None))

if __name__ == "__main__":
    main()
