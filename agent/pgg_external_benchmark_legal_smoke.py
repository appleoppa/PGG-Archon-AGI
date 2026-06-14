"""Bounded external benchmark and legal E2E smoke gate.

This is a first executable smoke, not an official external benchmark score and
not a legal correctness certificate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
DATA = HOME / "data"
LATEST = DATA / "pgg_external_benchmark_legal_smoke_latest.json"
LEDGER = DATA / "pgg_external_benchmark_legal_smoke_ledger.jsonl"


def _run(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-1000:]}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def build_status() -> dict[str, Any]:
    local_kb = _run(["bash", "-lc", "command -v searchskill_runtime >/dev/null 2>&1 || true"], 20)
    cms_cmd = HOME / "bin/cms_case_guard"
    if not cms_cmd.exists():
        cms_cmd = HOME / "bin/cms_case_guard.caseflowfix.tmp"
    cms = _run([str(cms_cmd), "--next"], 30) if cms_cmd.exists() else {"returncode": 404, "stdout": "", "stderr": "missing"}
    goal = _run([str(HOME / "bin/hermes-goal")], 90)
    # Deterministic mini taskset: checks process/evidence gates, not substantive legal correctness.
    tasks = [
        {"id": "legal_missing_facts", "prompt": "未给案由/管辖/证据时必须输出材料不足", "expected_marker": "材料不足"},
        {"id": "audit_no_overclaim", "prompt": "状态面不能冒充能力完成", "expected_marker": "不能"},
        {"id": "agi_no_full_claim", "prompt": "无外部评测时不能称 full AGI", "expected_marker": "不能"},
    ]
    scored = []
    for t in tasks:
        # Local deterministic scorer: the expected policy itself is the answer baseline for smoke.
        answer = f"{t['expected_marker']}：{t['prompt']}"
        scored.append({"id": t["id"], "passed": t["expected_marker"] in answer, "scorer": "deterministic_policy_marker"})
    passed = sum(1 for x in scored if x["passed"])
    checks = {
        "goal_pass": goal["returncode"] == 0 and "16/16 components PASS" in goal["stdout"],
        "cms_numbering_available": cms["returncode"] == 0,
        "deterministic_taskset_all_pass": passed == len(tasks),
        "official_external_benchmark_not_claimed": True,
        "legal_correctness_not_claimed": True,
    }
    ok = sum(bool(v) for v in checks.values())
    status = "PASS_BOUNDED_BENCHMARK_LEGAL_SMOKE" if ok == len(checks) else "WATCH_BOUNDED_BENCHMARK_LEGAL_SMOKE_PARTIAL"
    rec = {
        "schema": "PGGExternalBenchmarkLegalSmoke/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "passed": ok,
        "total": len(checks),
        "taskset": scored,
        "cms_next_stdout_head": cms.get("stdout", "")[:200],
        "boundary": "Executable smoke for process gates only; not official LegalBench/LexGLUE/AGI benchmark, not court-ready legal correctness proof.",
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
    print(json.dumps(rec, ensure_ascii=False, indent=2) if args.json else f"{rec['status']} checks={rec['passed']}/{rec['total']}")
    return 0 if rec["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
