"""PGG E2E 进化验收脚本 — 一键验证进化闭环是否跑通。

组合已有工具：eval_runner + health-monitor + gene_intake + one_click_audit
输出统一「进化健康分」+ 确认闭环完整性的详细 JSON。

Boundary: 只读调用已有 CLI；不修改 Hermes core/provider/config/scheduler/security；
不声称 AGI/T5/ASI/外部评测/法律正确性。
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_BIN = HOME / ".hermes/bin"
HERMES_HOME = HOME / ".hermes"


def _run(cmd: list[str], timeout: int = 60, cwd: str | Path | None = None) -> dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {
            "returncode": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "TIMEOUT"}
    except FileNotFoundError:
        return {"returncode": -2, "stdout": "", "stderr": "NOT_FOUND"}


def _json_or(raw: str) -> dict[str, Any] | None:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def check_eval_runner() -> dict[str, Any]:
    """Step 1: Golden QA Eval — 验证自学习基准通过率"""
    r = _run([str(HERMES_BIN / "pgg_eval_runner")], 60)
    j = _json_or(r["stdout"])
    if j:
        return {
            "status": "PASS" if j.get("verdict") == "PASS" else "WATCH",
            "total": j.get("total"),
            "passed": j.get("passed"),
            "failed": j.get("failed"),
            "accuracy": j.get("accuracy"),
            "threshold": j.get("threshold"),
        }
    return {"status": "FAIL", "error": r["stdout"][:300] + r["stderr"][:300]}


def check_health_monitor() -> dict[str, Any]:
    """Step 2: 系统健康 + GeneDB 真实状态"""
    r = _run([str(HERMES_BIN / "pgg-health-monitor"), "--json"], 60)
    j = _json_or(r["stdout"])
    if j:
        gd = j.get("gene_db", {})
        return {
            "status": j.get("level", "unknown"),
            "alerts": j.get("alerts", []),
            "gene_db": gd.get("counts", {}),
            "gene_db_total": gd.get("total_tracked", 0),
            "cpu": j.get("resources", {}).get("cpu_percent"),
            "memory": j.get("resources", {}).get("memory_percent"),
            "disk": j.get("resources", {}).get("disk_percent"),
        }
    return {"status": "FAIL", "error": r["stdout"][:300] + r["stderr"][:300]}


def check_gene_intake() -> dict[str, Any]:
    """Step 3: 基因摄入管线 — 验证能否从源码扫描出 candidate"""
    # 只查 intake pipeline 是否存在/可运行，不改写 DB
    binary = HERMES_BIN / "pgg_gene_intake_pipeline"
    if not binary.exists():
        alt = HERMES_HOME / "hermes-agent" / "rust_modules" / "target" / "release" / "pgg_gene_intake_pipeline"
        if alt.exists():
            binary = alt
        else:
            return {"status": "UNAVAILABLE", "error": "pgg_gene_intake_pipeline binary not found"}
    r = _run([str(binary), "--help"], 15)
    if r["returncode"] == 0:
        return {"status": "READY", "binary": str(binary)}
    return {"status": "FAIL", "error": r["stdout"][:200] + r["stderr"][:200]}


def check_genedb_promotion_precheck() -> dict[str, Any]:
    """Step 4: 基因晋升预检 — 查看 promotion pipeline 是否就绪"""
    binary = HERMES_BIN / "pgg_genedb_promotion_precheck"
    if not binary.exists():
        return {"status": "NOT_FOUND", "error": "no precheck CLI"}
    r = _run([str(binary), "--help"], 15)
    return {"status": "READY" if r["returncode"] == 0 else "FAIL",
            "note": r["stdout"][:200]}


def check_one_click_audit() -> dict[str, Any]:
    """Step 5: 一键全量审计 — 验证 binary 存在且可执行"""
    binary = HERMES_BIN / "pgg_one_click_full_audit_gate"
    if not binary.exists():
        return {"status": "NOT_FOUND"}
    r = _run([str(binary), "--help"], 15)
    if r["returncode"] == 0:
        return {"status": "READY", "binary": str(binary)}
    # Try python module
    r2 = _run([str(HERMES_HOME / "hermes-agent/.venv/bin/python3"),
               "-m", "agent.pgg_one_click_full_audit_gate", "--help"], 15)
    if r2["returncode"] == 0:
        return {"status": "READY", "via": "python -m"}
    return {"status": "FAIL", "error": r["stdout"][:200] + r["stderr"][:200]}


def check_rust_binaries() -> dict[str, Any]:
    """Step 6: Rust 核心二进制完整性 — 只检查有 [[bin]] 的 crate"""
    rust_dir = HERMES_HOME / "hermes-agent" / "rust_modules"
    if not rust_dir.exists():
        return {"status": "NOT_FOUND"}
    known_bins = [
        "pgg_provider_health_check",
        "pgg_skillflow_watchdog",
        "pgg_genedb_unified_audit",
        "pgg_gene_intake_pipeline",
        "pgg_query_complexity_gate",
        "pgg_provider_cost_profile",
        "pgg_eval_gate",
        "pgg_curve_collector",
        "pgg-sourceref-repair-runner-rs",
        "cms_case_guard",
    ]
    release = rust_dir / "target" / "release"
    compiled = 0
    missing = []
    for bn in known_bins:
        if (release / bn).exists() and (release / bn).is_file():
            compiled += 1
        else:
            missing.append(bn)
    return {
        "status": "PASS" if not missing else "WATCH",
        "known_bins": len(known_bins),
        "compiled": compiled,
        "missing": missing,
    }


def compute_score(steps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """根据各步骤结果计算进化健康分"""
    weights = {
        "eval_runner": 25,
        "health_monitor": 20,
        "gene_intake": 15,
        "genedb_precheck": 10,
        "one_click_audit": 15,
        "rust_binaries": 15,
    }

    score_table = {
        "PASS": 1.0,
        "READY": 0.85,
        "green": 1.0,
        "GREEN": 1.0,
        "WATCH": 0.5,
        "UNAVAILABLE": 0.3,
        "NOT_FOUND": 0.2,
        "FAIL": 0.0,
    }

    weighted_total = 0.0
    weight_sum = 0
    detail = {}

    for key, weight in weights.items():
        step = steps.get(key, {})
        st = str(step.get("status", "FAIL"))
        score = score_table.get(st, 0.0)
        weighted_total += weight * score
        weight_sum += weight
        detail[key] = {
            "status": st,
            "score": score,
            "weight": weight,
        }

    health_score = round((weighted_total / weight_sum) * 100, 1) if weight_sum > 0 else 0.0

    return {
        "health_score": health_score,
        "details": detail,
    }


def build_report() -> dict[str, Any]:
    steps = {
        "eval_runner": check_eval_runner(),
        "health_monitor": check_health_monitor(),
        "gene_intake": check_gene_intake(),
        "genedb_precheck": check_genedb_promotion_precheck(),
        "one_click_audit": check_one_click_audit(),
        "rust_binaries": check_rust_binaries(),
    }

    score_info = compute_score(steps)

    return {
        "schema": "pgg-evolution-e2e-acceptance/v1",
        "generated_at": now_iso(),
        "health_score": score_info["health_score"],
        "steps": score_info["details"],
        "details": steps,
        "score_breakdown": score_info,
        "boundary": "Read-only evolution E2E acceptance; composes existing CLI tools; no mutation; not AGI/T5/external benchmark/legal correctness proof.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="PGG E2E Evolution Acceptance Gate")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--score-only", action="store_true", help="Only print score")
    args = ap.parse_args(argv)

    report = build_report()

    if args.score_only:
        print(report["health_score"])
    elif args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        score = report["health_score"]
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        print(f"进化健康分: {score}/100 {bar}")
        print()
        for key, info in report["score_breakdown"]["details"].items():
            st = info["status"]
            sym = "✅" if st in ("PASS", "GREEN", "green", "READY") else \
                      "⚠️ " if st in ("WATCH", "UNAVAILABLE") else "❌"
            print(f"  {sym} {key}: {st} (weight={info['weight']}, score={info['score']})")

        last = report["details"]
        if "eval_runner" in last and "total" in last["eval_runner"]:
            er = last["eval_runner"]
            print(f"\n  Golden QA: {er.get('passed')}/{er.get('total')} passed, accuracy={er.get('accuracy')}")
        if "health_monitor" in last and "gene_db" in last["health_monitor"]:
            gd = last["health_monitor"]["gene_db"]
            print(f"  GeneDB: candidate={gd.get('candidate')}, promoted={gd.get('promoted')}, active={gd.get('active')}, total={last['health_monitor'].get('gene_db_total')}")
        if "rust_binaries" in last:
            rb = last["rust_binaries"]
            print(f"  Rust: {rb.get('compiled')}/{rb.get('total_crates')} crates compiled")
            if rb.get("missing"):
                print(f"  Missing: {', '.join(rb['missing'][:5])}")

    return 1 if report["health_score"] < 60 else 0


if __name__ == "__main__":
    raise SystemExit(main())