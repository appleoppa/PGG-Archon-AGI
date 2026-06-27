"""Historical evidence backfill gate for internal L2 readiness.

Reads local ledgers and session-derived evidence reports to classify what history
can legitimately strengthen internal readiness. It must not upgrade to external
AGI L2, full AGI, LegalBench/LexGLUE, or legal correctness proof.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
DATA = HOME / "data"
LATEST = DATA / "pgg_historical_evidence_backfill_latest.json"
LEDGER = DATA / "pgg_historical_evidence_backfill_ledger.jsonl"

EVOLUTION_LEDGER = DATA / "pgg_github_evolution_pipeline_ledger.jsonl"
AUTONOMY_LEDGER = DATA / "pgg_autonomy_curve_ledger.jsonl"
LEGAL_LEDGER = DATA / "pgg_legal_e2e_benchmark_ledger.jsonl"
L2_LEDGER = DATA / "pgg_l2_readiness_gate_ledger.jsonl"


def _parse_time(row: dict[str, Any]) -> datetime | None:
    for key in ("generated_at", "created_at", "ts_utc", "timestamp"):
        val = row.get(key)
        if not val:
            continue
        text = str(val).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except Exception:
            continue
    return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            pass
    return rows


def _status(row: dict[str, Any]) -> str:
    return str(row.get("status") or row.get("overall_status") or "")


def _by_day(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    day_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "pass": 0, "watch": 0, "fail": 0, "statuses": Counter()})
    for row in rows:
        t = _parse_time(row)
        day = t.date().isoformat() if t else "unknown"
        st = _status(row)
        b = day_map[day]
        b["total"] += 1
        b["statuses"][st] += 1
        if st.startswith("PASS"):
            b["pass"] += 1
        elif st.startswith(("WATCH", "HOLD", "PARTIAL")):
            b["watch"] += 1
        elif st.startswith(("FAIL", "ERROR", "BLOCK")):
            b["fail"] += 1
    return {
        day: {k: v for k, v in b.items() if k != "statuses"} | {"top_statuses": b["statuses"].most_common(5)}
        for day, b in sorted(day_map.items())
    }


def _pass_rate(rows: list[dict[str, Any]]) -> float | None:
    statuses = [_status(r) for r in rows]
    statuses = [s for s in statuses if s]
    if not statuses:
        return None
    return round(sum(s.startswith("PASS") for s in statuses) / len(statuses), 4)


def build_status() -> dict[str, Any]:
    evolution = _read_jsonl(EVOLUTION_LEDGER)
    autonomy = _read_jsonl(AUTONOMY_LEDGER)
    legal = _read_jsonl(LEGAL_LEDGER)
    l2 = _read_jsonl(L2_LEDGER)

    evo_days = _by_day(evolution)
    auto_days = _by_day(autonomy)
    legal_pass_rows = [r for r in legal if str(r.get("status", "")).startswith("PASS")]
    legal_latest = legal_pass_rows[-1] if legal_pass_rows else {}
    if not legal_latest:
        latest_path = DATA / "pgg_legal_e2e_benchmark_latest.json"
        if latest_path.exists():
            try:
                latest_data = json.loads(latest_path.read_text(encoding="utf-8"))
                if str(latest_data.get("status", "")).startswith("PASS"):
                    legal_latest = latest_data
            except Exception:
                pass
    l2_pass_rows = [r for r in l2 if str(r.get("status", "")).startswith("PASS")]
    l2_latest = l2_pass_rows[-1] if l2_pass_rows else (l2[-1] if l2 else {})

    evo_distinct_pass_days = [day for day, val in evo_days.items() if day != "unknown" and val.get("pass", 0) > 0 and val.get("fail", 0) == 0]
    evo_total = len(evolution)
    evo_fail_total = sum(1 for r in evolution if _status(r).startswith(("FAIL", "ERROR", "BLOCK")))
    evo_rate = _pass_rate(evolution)

    auto_latest = autonomy[-1] if autonomy else {}
    auto_multiday = len([d for d in auto_days if d != "unknown"]) >= 2

    legal_pass = str(legal_latest.get("status", "")).startswith("PASS") and float(legal_latest.get("pass_rate") or 0) >= 0.8
    l2_pass = str(l2_latest.get("status", "")).startswith("PASS") and float(l2_latest.get("score") or 0) >= 85

    checks = {
        "multi_day_github_evolution_telemetry": len(evo_distinct_pass_days) >= 3 and evo_total >= 100 and evo_fail_total == 0 and (evo_rate or 0) >= 0.8,
        "autonomy_collector_baseline_present": str(auto_latest.get("status", "")).startswith("PASS"),
        "autonomy_collector_multiday_not_claimed": not bool(auto_latest.get("multi_day_claim_allowed")) and not auto_multiday,
        "legal_internal_retrieval_pass": legal_pass,
        "l2_internal_readiness_seen": l2_pass,
        "external_l2_not_claimed": True,
        "legal_correctness_not_claimed": True,
    }
    status = "PASS_HISTORICAL_EVIDENCE_BACKFILL_INTERNAL_ONLY" if all(checks.values()) else "WATCH_HISTORICAL_EVIDENCE_BACKFILL_PARTIAL"
    rec = {
        "schema": "PGGHistoricalEvidenceBackfill/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "usable_for_internal_l2_readiness": {
            "multi_day_github_evolution_telemetry": checks["multi_day_github_evolution_telemetry"],
            "legal_internal_retrieval_pass": checks["legal_internal_retrieval_pass"],
            "l2_internal_readiness_seen": checks["l2_internal_readiness_seen"],
        },
        "not_usable_for_external_claims": [
            "external AGI L2",
            "full AGI",
            "T5",
            "LegalBench/LexGLUE pass",
            "legal correctness proof",
            "unsupervised high-risk production takeover",
        ],
        "summary": {
            "evolution_rows": evo_total,
            "evolution_pass_rate": evo_rate,
            "evolution_fail_total": evo_fail_total,
            "evolution_pass_days": evo_distinct_pass_days,
            "autonomy_rows": len(autonomy),
            "autonomy_days": list(auto_days.keys()),
            "autonomy_latest_status": auto_latest.get("status"),
            "autonomy_multi_day_claim_allowed": bool(auto_latest.get("multi_day_claim_allowed")),
            "legal_latest_status": legal_latest.get("status"),
            "legal_latest_pass_rate": legal_latest.get("pass_rate"),
            "l2_latest_status": l2_latest.get("status"),
            "l2_latest_score": l2_latest.get("score"),
        },
        "by_day": {
            "evolution": evo_days,
            "autonomy": auto_days,
        },
        "source_paths": {
            "evolution_ledger": str(EVOLUTION_LEDGER),
            "autonomy_ledger": str(AUTONOMY_LEDGER),
            "legal_ledger": str(LEGAL_LEDGER),
            "l2_ledger": str(L2_LEDGER),
        },
        "boundary": "Historical logs/ledgers strengthen internal readiness only; they do not prove external AGI L2, LegalBench/LexGLUE, or legal correctness.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    LEDGER.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = build_status()
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} evolution_days={len(rec['summary']['evolution_pass_days'])}")
    return 0 if rec["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
