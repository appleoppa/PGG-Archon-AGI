"""SE19 SkillFlow live observation anti-fabrication gate.

Only observations explicitly tagged as real_live count toward the 50/100 live window.
Shadow canary, replay, benchmark, and test_smoke records are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from agent.pgg_skillflow_advisor import advise

LEDGER = Path.home() / ".hermes/data/pgg_skillflow_live_observation_ledger.jsonl"
STATUS = Path.home() / ".hermes/data/pgg_skillflow_live_window_status.json"
BOUNDARY = "Anti-fabrication live-window gate: strict live observations exclude bulk/read-only harvesting; no route enforcement, no answer-chain replacement."
VALID_KINDS = {"real_live", "test_smoke", "shadow", "replay", "benchmark"}


def classify_observation(task_text: str, evidence: str, kind: str) -> dict[str, Any]:
    """Classify observation granularity to prevent bulk overcount."""
    blob = f"{task_text} {evidence}".lower()
    bulk_markers = [
        "raw_oss_to_100",
        "continuous_oss_to_100",
        "github raw",
        "bulk oss",
        "连续到100 raw开源观察",
        "readme读取成功",
        "读取成功，patterns=",
    ]
    weak = not evidence or evidence.startswith("current_user_turn")
    wrong_path = "omniroute_v76_policy_ledger.jsonl" in evidence
    is_bulk = any(x in blob for x in bulk_markers)
    if kind != "real_live":
        return {"evidence_class": kind, "granularity": "non_live", "strict_counts_toward_live_window": False, "reason": "non_real_live_kind"}
    if weak:
        return {"evidence_class": "weak_or_missing_evidence", "granularity": "weak", "strict_counts_toward_live_window": False, "reason": "missing_or_placeholder_evidence"}
    if wrong_path:
        return {"evidence_class": "wrong_evidence_path", "granularity": "repair_required", "strict_counts_toward_live_window": False, "reason": "known_wrong_ledger_path"}
    if is_bulk:
        return {"evidence_class": "bulk_oss_harvest", "granularity": "batch_or_repo_readonly", "strict_counts_toward_live_window": False, "reason": "bulk_readonly_oss_not_live_task"}
    return {"evidence_class": "task_level_evidence", "granularity": "task", "strict_counts_toward_live_window": True, "reason": "task_level_real_live_with_evidence"}


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def _strict_row_counts(r: dict[str, Any]) -> bool:
    if r.get("kind") != "real_live" or r.get("counts_toward_live_window") is not True:
        return False
    if "strict_counts_toward_live_window" in r:
        return r.get("strict_counts_toward_live_window") is True
    cls = classify_observation(str(r.get("task_text") or ""), str(r.get("evidence") or ""), str(r.get("kind") or ""))
    return cls.get("strict_counts_toward_live_window") is True


def status() -> dict[str, Any]:
    rows = _rows()
    mechanical_live = [r for r in rows if r.get("counts_toward_live_window") is True and r.get("kind") == "real_live"]
    live = [r for r in mechanical_live if _strict_row_counts(r)]
    bulk_excluded = sum(1 for r in mechanical_live if not _strict_row_counts(r) and classify_observation(str(r.get("task_text") or ""), str(r.get("evidence") or ""), str(r.get("kind") or "")).get("evidence_class") == "bulk_oss_harvest")
    weak_excluded = sum(1 for r in mechanical_live if not _strict_row_counts(r) and classify_observation(str(r.get("task_text") or ""), str(r.get("evidence") or ""), str(r.get("kind") or "")).get("evidence_class") in {"weak_or_missing_evidence", "wrong_evidence_path"})
    non_live = len(rows) - len(mechanical_live)
    collapse = sum(1 for r in live if r.get("collapse_risk"))
    unsafe = sum(1 for r in live if r.get("production_answer_chain_replaced") or r.get("route_enforce"))
    n = len(live)
    mechanical_n = len(mechanical_live)
    st = {
        "schema": "PGGSkillFlowLiveWindowStatus/v2",
        "status": "PASS_STABLE_LIVE_WINDOW" if n >= 100 and collapse == 0 and unsafe == 0 else ("PASS_INITIAL_LIVE_WINDOW" if n >= 50 and collapse == 0 and unsafe == 0 else "WATCH_LIVE_WINDOW_INSUFFICIENT"),
        "real_live_count": n,
        "mechanical_live_count": mechanical_n,
        "bulk_oss_excluded_count": bulk_excluded,
        "weak_or_wrong_evidence_excluded_count": weak_excluded,
        "non_live_excluded_count": non_live,
        "minimum_initial": 50,
        "minimum_stable": 100,
        "remaining_to_initial": max(0, 50 - n),
        "remaining_to_stable": max(0, 100 - n),
        "collapse_risk_count": collapse,
        "unsafe_enforcement_count": unsafe,
        "ledger": str(LEDGER),
        "production_answer_chain_replaced": False,
        "route_enforce": False,
        "boundary": BOUNDARY,
    }
    st["summary_zh"] = f"SE19 live窗口门禁：{st['status']}；strict_real_live {n}/50初始、{n}/100稳定；mechanical={mechanical_n}；bulk排除 {bulk_excluded}；弱证据排除 {weak_excluded}；坍塌 {collapse}；unsafe_enforcement {unsafe}；production_answer_chain_replaced=false；route_enforce=false。"
    STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return st


def append(task_text: str, outcome: str = "UNKNOWN", adopted: bool | None = None, kind: str = "real_live", evidence: str = "") -> dict[str, Any]:
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid kind {kind}; expected {sorted(VALID_KINDS)}")
    adv = advise(task_text)
    cls = classify_observation(task_text, evidence, kind)
    row = {
        "schema": "PGGSkillFlowLiveObservation/v2",
        "ts": time.time(),
        "observation_id": "live:" + hashlib.sha256(f"{time.time()}:{task_text}:{kind}".encode()).hexdigest()[:16],
        "kind": kind,
        "counts_toward_live_window": kind == "real_live",
        "strict_counts_toward_live_window": cls["strict_counts_toward_live_window"],
        "evidence_class": cls["evidence_class"],
        "granularity": cls["granularity"],
        "classification_reason": cls["reason"],
        "task_text": task_text,
        "task_class": adv["task_class"],
        "risk_flags": adv["risk_flags"],
        "selected_advisory_route": adv["selected_advisory_route"],
        "collapse_risk": adv["policy"].get("collapse_risk"),
        "adopted": adopted,
        "outcome": outcome,
        "evidence": evidence,
        "production_answer_chain_replaced": False,
        "route_enforce": False,
        "boundary": BOUNDARY,
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"observation": row, "status": status()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="继续完成 SE19 最大合规闭环")
    ap.add_argument("--kind", default="real_live", choices=sorted(VALID_KINDS))
    ap.add_argument("--outcome", default="UNKNOWN")
    ap.add_argument("--adopted", choices=["true", "false", "unknown"], default="unknown")
    ap.add_argument("--evidence", default="")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ns = ap.parse_args(argv)
    if ns.status:
        out = status()
    else:
        adopted = None if ns.adopted == "unknown" else ns.adopted == "true"
        out = append(ns.task, ns.outcome, adopted, ns.kind, ns.evidence)
    print(out["summary_zh"] if ns.summary and "summary_zh" in out else (out["status"]["summary_zh"] if ns.summary and "status" in out else json.dumps(out, ensure_ascii=False, indent=2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
