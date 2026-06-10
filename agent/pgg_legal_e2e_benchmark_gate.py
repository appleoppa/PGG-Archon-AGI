"""Bounded legal E2E benchmark gate for PGG L2-readiness.

This gate runs deterministic retrieval tasks against the local official/legal
corpus. It proves that the workflow can locate and cite local legal sources for
a small taskset. It does not certify legal correctness and is not LegalBench.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
CORPUS_ROOT = HOME / "workspace/智库/法律法规库"
DATA = HOME / "data"
LATEST = DATA / "pgg_legal_e2e_benchmark_latest.json"
LEDGER = DATA / "pgg_legal_e2e_benchmark_ledger.jsonl"

TASKS = [
    {
        "id": "labor_dispute_interpretation_1",
        "query": "最高人民法院关于审理劳动争议案件适用法律问题的解释（一）",
        "required_terms": ["劳动争议", "解释（一）"],
        "filename_terms": ["解释（一）"],
    },
    {
        "id": "traffic_damage_interpretation_2",
        "query": "最高法关于审理道路交通事故损害赔偿案件适用法律若干问题的解释二",
        "required_terms": ["道路交通事故", "损害赔偿", "解释二"],
    },
    {
        "id": "refuse_execute_criminal_interpretation",
        "query": "拒不执行判决、裁定刑事案件适用法律若干问题的解释",
        "required_terms": ["拒不执行判决", "裁定", "刑事案件"],
    },
    {
        "id": "delayed_performance_interest_execution",
        "query": "执行程序中计算迟延履行期间的债务利息适用法律若干问题的解释",
        "required_terms": ["迟延履行", "债务利息", "执行程序"],
    },
    {
        "id": "property_service_dispute_interpretation",
        "query": "审理物业服务纠纷案件具体应用法律若干问题的解释",
        "required_terms": ["物业服务", "纠纷", "解释"],
    },
]


def _candidate_files() -> list[Path]:
    if not CORPUS_ROOT.exists():
        return []
    return [p for p in CORPUS_ROOT.rglob("*.txt") if p.is_file()]


def _score_task(task: dict[str, Any], files: list[Path]) -> dict[str, Any]:
    q = task["query"]
    best: tuple[int, Path | None, str] = (0, None, "")
    q_terms = [t for t in q.replace("、", " ").replace("，", " ").split() if t]
    for p in files:
        name = p.name
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")[:5000]
        except Exception:
            continue
        hay = name + "\n" + text
        filename_ok = all(term in name for term in task.get("filename_terms", []))
        score = 0
        if not filename_ok:
            continue
        for term in task["required_terms"]:
            if term in hay:
                score += 2
        for term in q_terms:
            if term and term in hay:
                score += 1
        if score > best[0]:
            best = (score, p, text[:500])
    score, path, snippet = best
    required_hits = sum(1 for t in task["required_terms"] if path and t in (path.name + "\n" + snippet))
    passed = path is not None and required_hits >= max(1, len(task["required_terms"]) - 1)
    return {
        "id": task["id"],
        "passed": passed,
        "score": score,
        "required_hits": required_hits,
        "required_total": len(task["required_terms"]),
        "source_path": str(path) if path else None,
        "snippet_head": snippet[:180] if path else "",
    }


def run_benchmark() -> dict[str, Any]:
    files = _candidate_files()
    results = [_score_task(t, files) for t in TASKS]
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pass_rate = round(passed / total, 4) if total else 0.0
    checks = {
        "corpus_present": CORPUS_ROOT.exists() and len(files) > 0,
        "taskset_nonempty": total >= 5,
        "pass_rate_ge_0_80": pass_rate >= 0.80,
        "source_paths_recorded": all(r.get("source_path") for r in results if r["passed"]),
        "not_external_legal_correctness_claim": True,
    }
    status = "PASS_BOUNDED_LEGAL_E2E_RETRIEVAL_BENCHMARK" if all(checks.values()) else "WATCH_BOUNDED_LEGAL_E2E_RETRIEVAL_BENCHMARK"
    rec = {
        "schema": "PGGLegalE2EBenchmark/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "corpus_root": str(CORPUS_ROOT),
        "corpus_file_count": len(files),
        "passed": passed,
        "total": total,
        "pass_rate": pass_rate,
        "results": results,
        "boundary": "Local official/legal corpus retrieval benchmark; not LegalBench, not legal correctness proof, not external certification.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    LEDGER.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = run_benchmark()
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} pass_rate={rec['pass_rate']}")
    return 0 if rec["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
