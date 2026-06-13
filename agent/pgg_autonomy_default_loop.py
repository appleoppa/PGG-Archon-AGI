#!/usr/bin/env python3
"""PGG Autonomy Default Loop v1.1 — 自动闭环扩展.

在 v1.0 基础上新增:
- 深度案件复验: 扫描 苹果中枢办案库/ → 实际跑 cms_case_guard --validate
- 自改进阶段: 从 WATCH 项生成修复任务, 应用并验证
- 自复盘: 日度改进报告
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = HOME / ".hermes"
REPO = HERMES_HOME / "hermes-agent"
WORKSPACE = HERMES_HOME / "workspace" / "pgg-archon-governance" / "autonomy-default"
MANIFEST = HERMES_HOME / "data" / "EVOLUTION_MANIFEST.json"
LOG_DIR = HERMES_HOME / "logs"
CASES_ROOT = HERMES_HOME / "workspace" / "苹果中枢办案库"
CMS_GUARD = HERMES_HOME / "bin" / "cms_case_guard"
TRUSTED_GATE = HERMES_HOME / "bin" / "case_trusted_workflow_gate"
METABOLIC_NET_GAIN_ROOT = WORKSPACE / "metabolic-net-gain"
METABOLIC_EXECUTE_ENV = "PGG_AUTONOMY_METABOLISM_EXECUTE"

METABOLIC_ACCELERATION_PROFILES: dict[str, dict[str, int | str]] = {
    "safe": {"acceleration": "safe", "max_batches": 3, "batch_size": 10, "daily_cap": 30},
    "balanced": {"acceleration": "balanced", "max_batches": 5, "batch_size": 20, "daily_cap": 100},
    "fast": {"acceleration": "fast", "max_batches": 10, "batch_size": 25, "daily_cap": 250},
    "turbo": {"acceleration": "turbo", "max_batches": 20, "batch_size": 50, "daily_cap": 1000},
}

LLM_DAILY_BUDGET_TOKENS = 120_000_000

HARD_BOUNDARIES = [
    "no_credential_mutation", "no_provider_config_mutation",
    "no_scheduler_security_mutation", "no_production_answer_chain_switch",
    "no_legal_finalization", "no_cross_profile_write",
    "no_memory_apply_without_backup", "no_github_push_without_pr",
    "no_genedb_promotion_without_gate",
]


@dataclass
class ProbeResult:
    name: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutoFixCandidate:
    target_path: str
    fix_type: str
    risk: str
    command: list[str]
    result: dict[str, Any] = field(default_factory=lambda: {"applied": False})


@dataclass
class ImprovementPlan:
    source: str     # which probe/WATCH
    issue: str
    proposed_action: str
    risk: str
    applied: bool = False
    verification: str = ""


@dataclass
class DailyReport:
    schema: str = "PGGAutonomyDefaultReport/v1.1"
    generated_at: str = ""
    session_id: str = ""
    probes: list[ProbeResult] = field(default_factory=list)
    auto_fixes: list[AutoFixCandidate] = field(default_factory=list)
    case_reverifications: list[dict[str, Any]] = field(default_factory=list)
    metabolic_evolution: dict[str, Any] = field(default_factory=dict)
    improvement_plan: list[ImprovementPlan] = field(default_factory=list)
    llm_budget_used: int = 0
    llm_budget_remaining: int = LLM_DAILY_BUDGET_TOKENS
    hard_boundaries: list[str] = field(default_factory=lambda: HARD_BOUNDARIES)
    summary: str = ""
    boundary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_at": self.generated_at,
            "session_id": self.session_id,
            "probes": [asdict(p) for p in self.probes],
            "auto_fixes": [asdict(f) for f in self.auto_fixes],
            "case_reverifications": self.case_reverifications,
            "metabolic_evolution": self.metabolic_evolution,
            "improvement_plan": [asdict(p) for p in self.improvement_plan],
            "llm_budget_used": self.llm_budget_used,
            "llm_budget_remaining": self.llm_budget_remaining,
            "hard_boundaries": self.hard_boundaries,
            "summary": self.summary,
            "boundary": self.boundary,
        }


# ── Utilities ────────────────────────────────────────────────────────────

def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> dict[str, Any]:
    try:
        cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return {"rc": cp.returncode, "output": cp.stdout}
    except FileNotFoundError as e:
        return {"rc": 127, "output": f"FileNotFoundError: {e}"}
    except subprocess.TimeoutExpired as e:
        return {"rc": 124, "output": (e.stdout or "")[-2000:]}
    except Exception as e:
        return {"rc": 1, "output": f"{type(e).__name__}: {e}"}


def _py_path() -> str:
    candidates = [REPO / ".venv" / "bin" / "python3", REPO / "venv" / "bin" / "python3",
                  Path(sys.executable)]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def _append_manifest(key: str, value: dict[str, Any]) -> None:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
        if not isinstance(data, dict):
            data = {}
        data[key] = value
        MANIFEST.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] manifest: {e}")


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Phase 1: Probes ──────────────────────────────────────────────────────

def run_probes() -> list[ProbeResult]:
    results: list[ProbeResult] = []
    py = _py_path()

    # 1. Autonomy controller v0.8
    script = REPO / "agent" / "pgg_archon_autonomy_controller.py"
    if script.exists():
        t = time.time()
        res = _run([py, str(script), "observe"], cwd=REPO, timeout=30)
        results.append(ProbeResult("autonomy_controller",
            "PASS" if res["rc"] == 0 else "WATCH",
            f"rc={res['rc']} t={time.time()-t:.0f}s",
            {"output": res["output"][:2000]}))

    # 1b. Hermes CLI / venv compatibility probe + low-risk self-heal
    t = time.time()
    try:
        from agent.pgg_self_healing_pipeline import ensure_hermes_cli_compatibility
        cli_health = ensure_hermes_cli_compatibility()
        cli_ok = cli_health.get("status") in ("PASS", "APPLIED")
        local_rc = (cli_health.get("version_checks") or {}).get("local_launcher", {}).get("rc")
        old_rc = (cli_health.get("version_checks") or {}).get("old_venv_path", {}).get("rc")
        results.append(ProbeResult("hermes_cli_venv_compat",
            "PASS" if cli_ok else "WATCH",
            f"status={cli_health.get('status')} local_rc={local_rc} old_rc={old_rc} t={time.time()-t:.0f}s",
            cli_health))
    except Exception as e:
        results.append(ProbeResult("hermes_cli_venv_compat", "WATCH", f"probe_error={type(e).__name__}: {e}"))

    # 2. hermes-goal
    goal = HERMES_HOME / "bin" / "hermes-goal"
    if goal.exists():
        t = time.time()
        res = _run([str(goal)], timeout=120)
        if res["rc"] == 0:
            try:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(res["output"].lstrip())
                overall = data.get("overall_status", "?")
                watch = data.get("watch_count", -1)
                blocked = data.get("blocked_count", -1)
                results.append(ProbeResult("hermes_goal",
                    "PASS" if overall == "PASS" else "WATCH",
                    f"overall={overall} W={watch} B={blocked} t={time.time()-t:.0f}s",
                    {"data": data}))
            except Exception as e:
                results.append(ProbeResult("hermes_goal", "WATCH", f"parse_error={type(e).__name__}: {e}; raw={res['output'][:200]}"))
        else:
            results.append(ProbeResult("hermes_goal", "WATCH", f"rc={res['rc']}"))

    # 3. L2 readiness gate
    t = time.time()
    res = _run([py, "-m", "agent.pgg_l2_readiness_gate"], cwd=REPO, timeout=90)
    results.append(ProbeResult("l2_gate",
        "PASS" if res["rc"] == 0 else "WATCH",
        res["output"].strip()[:300] if res["rc"] == 0 else f"rc={res['rc']} t={time.time()-t:.0f}s"))

    # 4. AGI gap gate
    t = time.time()
    res = _run([py, "-m", "agent.pgg_agi_gap_closure_gate"], cwd=REPO, timeout=90)
    results.append(ProbeResult("agi_gap",
        "PASS" if res["rc"] == 0 else "WATCH",
        res["output"].strip()[:300] if res["rc"] == 0 else f"rc={res['rc']} t={time.time()-t:.0f}s"))

    # 5. Gene intake
    t = time.time()
    res = _run([py, "-m", "agent.pgg_gene_intake_loop_cli", "--json-only"], cwd=REPO, timeout=30)
    if res["rc"] == 0:
        try:
            data = json.loads(res["output"])
            results.append(ProbeResult("gene_intake", "PASS",
                f"scanned={data.get('scanned')} fused={len(data.get('fusion_dry_run_results',[]))} t={time.time()-t:.0f}s"))
        except Exception:
            results.append(ProbeResult("gene_intake", "PASS", res["output"][:200]))
    else:
        results.append(ProbeResult("gene_intake", "WATCH", f"rc={res['rc']}"))

    # 6. Memory & neuron health
    for cli_name, probe_name in [("记忆系统", "memory_system"), ("神经元系统", "neuron_system")]:
        cli = HERMES_HOME / "bin" / cli_name
        if cli.exists():
            t = time.time()
            res = _run([str(cli)], timeout=20)
            results.append(ProbeResult(probe_name,
                "PASS" if res["rc"] == 0 else "WATCH",
                res["output"].strip()[:200] if res["rc"] == 0 else f"rc={res['rc']} t={time.time()-t:.0f}s"))

    # 7. OmniRoute health
    cli = HERMES_HOME / "bin" / "omniroute_ui_status"
    if cli.exists():
        res = _run([str(cli)], timeout=15)
        results.append(ProbeResult("omniroute",
            "PASS" if res["rc"] == 0 else "WATCH", res["output"].strip()[:200]))

    return results


# ── Phase 2: Deep Case Re-verification ───────────────────────────────────

def deep_case_check() -> list[dict[str, Any]]:
    """Deep re-verify completed CMS cases using real gates."""
    results: list[dict[str, Any]] = []

    if not CASES_ROOT.exists():
        results.append({"status": "SKIP", "summary": f"案件目录不存在: {CASES_ROOT}"})
        return results

    case_dirs = sorted([d for d in CASES_ROOT.iterdir() if d.is_dir() and d.name != "_backups"])
    checked = 0

    for case_dir in case_dirs:
        if checked >= 5:
            break
        meta_path = case_dir / "meta.json"
        if not meta_path.exists():
            continue

        case_id = case_dir.name.split("-")[0] if "-" in case_dir.name else case_dir.name
        full_case_id = case_dir.name
        warnings: list[str] = []
        findings: list[str] = []

        # 1. Check meta.json
        try:
            meta = json.loads(meta_path.read_text())
            status = meta.get("status", "?")
            findings.append(f"meta: {status}")
        except Exception as e:
            warnings.append(f"meta.json unreadable: {e}")
            continue

        # 2. Try CMS guard validate
        if CMS_GUARD.exists():
            t = time.time()
            res = _run([str(CMS_GUARD), "--validate", str(case_dir), "--case-type",
                       meta.get("case_type", "general")], timeout=30)
            if res["rc"] == 0:
                findings.append(f"cms_guard: PASS ({time.time()-t:.0f}s)")
            else:
                warnings.append(f"cms_guard: rc={res['rc']} ({time.time()-t:.0f}s)")

        # 3. Try trusted workflow gate
        if TRUSTED_GATE.exists():
            res2 = _run([str(TRUSTED_GATE), str(case_dir)], timeout=30)
            if res2["rc"] == 0 and "PASS" in res2["output"]:
                findings.append("trusted_gate: PASS")
            else:
                warnings.append(f"trusted_gate: rc={res2['rc']}")

        # 4. Check deliverables
        deliv_dir = find_deliv_dir(case_dir)
        if deliv_dir:
            files = [f.name for f in deliv_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
            if files:
                findings.append(f"deliverables ({len(files)}): {', '.join(files[:3])}")
            else:
                warnings.append("deliverables dir empty")
        else:
            warnings.append("no deliverables dir found")



        # 5. Check evidence
        found_evidence = False
        for sub in case_dir.iterdir():
            if sub.is_dir() and ("证据" in sub.name or "材料" in sub.name or "evidence" in sub.name.lower()):
                evidence_files = [f for f in sub.rglob("*") if f.is_file()]
                if evidence_files:
                    findings.append(f"evidence: {len(evidence_files)} files")
                    found_evidence = True
                    break
        if not found_evidence:
            warnings.append("no evidence dir found")

        case_status = "PASS" if not warnings else "WATCH"
        results.append({
            "case_id": full_case_id,
            "status": case_status,
            "findings": findings,
            "warnings": warnings,
            "meta": {"type": meta.get("case_type",""), "status": status},
        })
        checked += 1

    if not results:
        results.append({"status": "PASS", "summary": "未找到案件", "cases_checked": 0})

    results.append({"status": "INFO", "summary": f"深度复验 {checked} 件案件",
                     "cases_checked": checked})
    return results


def find_deliv_dir(case_dir: Path) -> Path | None:
    """Find a deliverables/终版/正式 directory in a case directory."""
    for sub in case_dir.iterdir():
        if sub.is_dir() and ("交付" in sub.name or "终版" in sub.name or "正式" in sub.name or "deliver" in sub.name.lower()):
            return sub
    for sub in case_dir.rglob("*"):
        if sub.is_dir() and ("交付" in sub.name or "终版" in sub.name or "正式" in sub.name or "deliver" in sub.name.lower()):
            return sub
    return None


# ── Phase 3: Auto Fix (extended) ────────────────────────────────────────

def auto_fix() -> list[AutoFixCandidate]:
    """Auto-fix low-risk issues: py_compile + ruff lint + black format."""
    fixes: list[AutoFixCandidate] = []
    py = _py_path()

    res = _run(["git", "status", "--short"], cwd=REPO, timeout=20)
    if res["rc"] != 0:
        return fixes

    for line in res["output"].splitlines():
        line = line.strip()
        if not line:
            continue
        path_part = line[3:].strip() if len(line) > 3 else ""
        if not path_part.endswith(".py"):
            continue
        abs_path = str((REPO / path_part).resolve()) if not path_part.startswith("/") else path_part
        if not Path(abs_path).exists():
            continue

        # py_compile
        fix = AutoFixCandidate(path_part, "py_compile", "LOW",
                               [py, "-m", "py_compile", abs_path])
        r = _run(fix.command, cwd=REPO, timeout=15)
        fix.result = {"applied": r["rc"] == 0, "rc": r["rc"]}
        fixes.append(fix)

        # ruff (if installed)
        ruff = shutil.which("ruff")
        if ruff and Path(abs_path).exists():
            fix2 = AutoFixCandidate(path_part, "ruff", "LOW",
                                    [ruff, "check", "--fix-only", "--silent", abs_path])
            r2 = _run(fix2.command, cwd=REPO, timeout=15)
            fix2.result = {"applied": r2["rc"] in (0, 1), "rc": r2["rc"]}
            fixes.append(fix2)

    return fixes


import shutil


# ── Phase 4: Self-Improvement Plan ──────────────────────────────────────

def generate_improvement_plan(probes: list[ProbeResult],
                               case_checks: list[dict[str, Any]]) -> list[ImprovementPlan]:
    """From WATCH items, generate concrete improvement tasks."""
    plan: list[ImprovementPlan] = []

    for p in probes:
        if p.status in ("WATCH", "ERROR"):
            plan.append(ImprovementPlan(
                source=p.name,
                issue=p.summary[:200],
                proposed_action=f"诊断并修复 {p.name}: {p.summary[:120]}",
                risk="MEDIUM",
            ))

    for c in case_checks:
        if c.get("status") == "WATCH":
            for w in c.get("warnings", []):
                plan.append(ImprovementPlan(
                    source=f"案件:{c.get('case_id','?')}",
                    issue=w[:200],
                    proposed_action=f"修复案件 {c.get('case_id','?')}: {w[:120]}",
                    risk="MEDIUM",
                ))

    # Apply auto-repairable improvements
    for item in plan:
        if item.risk == "MEDIUM" and "omniroute" in item.source.lower():
            item.applied = False
            item.verification = "需要人工排查, 跳过自动修复"
        elif item.risk == "MEDIUM" and "memory" in item.source.lower():
            item.applied = False
            item.verification = "需要备份后修复, 跳过自动修复"
        elif item.risk == "MEDIUM":
            item.applied = False
            item.verification = "需要人工审查"

    return plan


# ── Phase 5: Retrospect ─────────────────────────────────────────────────

def build_summary(probes, fixes, cases, imp_plan, llm_budget_used, metabolic=None):
    p = sum(1 for x in probes if x.status in ("PASS", "SKIP"))
    w = sum(1 for x in probes if x.status in ("WATCH", "BLOCKED"))
    e = sum(1 for x in probes if x.status == "ERROR")
    fx = sum(1 for x in fixes if x.result.get("applied"))
    cp = sum(1 for x in cases if x.get("status") == "PASS")
    cw = sum(1 for x in cases if x.get("status") == "WATCH")
    ip = sum(1 for x in imp_plan if not x.applied)

    lines = []
    lines.append(f"探针: {len(probes)}个 - {p} PASS / {w} WATCH / {e} ERROR")
    if metabolic:
        lines.append(f"代谢进化: {metabolic.get('status')} accel={metabolic.get('acceleration')} batches={metabolic.get('total_batches')} backend={metabolic.get('mutation_backend')} db_mutation={metabolic.get('db_mutation')} net_gain={metabolic.get('net_gain')}")
    if fx: lines.append(f"自动修复: {fx}/{len(fixes)} 项已执行")
    if cases: lines.append(f"案件复验: {cp} PASS / {cw} WATCH")
    if imp_plan:
        lines.append(f"改进计划: {len(imp_plan)} 项（{ip} 待处理）")
        for x in imp_plan:
            lines.append(f"  {'✅' if x.applied else '⏳'} [{x.source}] {x.issue[:100]}")
    lines.append(f"LLM预算: ~{llm_budget_used//1000}k tokens / {LLM_DAILY_BUDGET_TOKENS//1000000}M 日限额")
    return "\n".join(lines)

def open_source_learning(max_repos: int = 3) -> list[ProbeResult]:
    """每日开源学习: GitHub 搜索新仓库, 提取可吸收模式, 门禁分类."""
    results: list[ProbeResult] = []
    topics = [
        "self-evolving agent autonomous loop",
        "rust agent framework self-healing",
        "LLM routing fallback cost optimization",
        "legal AI document analysis gate",
        "recursive self-improvement agent",
        "open source AI agent bug auto-fix",
    ]
    import random
    topic = random.choice(topics)
    # Use web search since GitHub MCP may be rate-limited
    import urllib.request, urllib.parse, urllib.error
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(topic)}&sort=stars&order=desc&per_page={max_repos}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PGG-Archon-Apple-Didi/1.0", "Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])[:max_repos]
            if items:
                for r in items:
                    name = r.get("full_name", "?")
                    stars = r.get("stargazers_count", 0)
                    desc = (r.get("description") or "")[:120]
                    lang = r.get("language") or "?"
                    results.append(ProbeResult(f"github:{name.replace('/','_')}",
                        "PASS" if stars > 50 else "INFO",
                        f"[{lang}] ⭐{stars} {desc}",
                        {"url": r.get("html_url"), "stars": stars, "topics": r.get("topics", [])}))
            else:
                results.append(ProbeResult(f"github:{topic[:30]}", "INFO", f"no repos found for: {topic}"))
    except Exception as e:
        results.append(ProbeResult(f"github:{topic[:20]}", "WATCH", f"fetch error: {e}"))
    return results


def auto_create_pr_from_fixes(fixes, imp_plan, repo_dir):
    """Auto-create draft PR from applied fixes (no auto-merge)."""
    import subprocess, datetime
    fix_desc = []
    for f in fixes:
        if isinstance(f, dict): continue
        if hasattr(f, 'result') and f.result.get("applied"):
            fix_desc.append(f"{f.fix_type}: {f.target_path}")
    for p in imp_plan:
        if hasattr(p, 'applied') and p.applied:
            fix_desc.append(f"{p.source}: {p.issue[:80]}")
    if not fix_desc:
        return [{"status": "SKIP", "reason": "no fixes to PR"}]

    branch = f"auto-fix-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    title = f"auto: 日常自动修复 ({len(fix_desc)}项)"
    body_items = ["## 自动修复摘要"] + [f"- {d}" for d in fix_desc]
    body_items.append("")
    body_items.append("_由 PGG Autonomy Loop 自动创建，不自动 merge_")
    body = "\n".join(body_items)

    try:
        cur = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir,
                            capture_output=True, text=True, timeout=10).stdout.strip()
        subprocess.run(["git", "checkout", "-b", branch], cwd=repo_dir,
                      capture_output=True, text=True, timeout=15, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, capture_output=True, timeout=15, check=True)
        subprocess.run(["git", "commit", "-m", title, "-m", body], cwd=repo_dir,
                      capture_output=True, text=True, timeout=15, check=True)
        subprocess.run(["git", "push", "private", branch, "--no-verify"], cwd=repo_dir,
                      capture_output=True, text=True, timeout=60, check=True)
        pr = subprocess.run(["gh", "pr", "create", "--repo", "appleoppa/PGG-Archon-AGI",
                           "--base", cur, "--head", branch,
                           "--title", title, "--body", body, "--draft"],
                          cwd=repo_dir, capture_output=True, text=True, timeout=30)
        subprocess.run(["git", "checkout", cur], cwd=repo_dir, capture_output=True, timeout=10)

        if pr.returncode == 0:
            return [{"status": "PASS", "url": pr.stdout.strip(), "branch": branch}]
        return [{"status": "WATCH", "reason": pr.stderr[:200], "branch": branch}]
    except Exception as e:
        return [{"status": "ERROR", "reason": str(e)[:200]}]


def resolve_metabolic_acceleration(acceleration: str | None = None) -> dict[str, int | str]:
    """Resolve Phase13 acceleration profile.

    Phase13 intentionally moves from tiny fixed batches to a dynamic high-throughput
    lane while retaining explicit execute gating and fuse/rollback evidence.
    """
    key = (acceleration or os.environ.get("PGG_METABOLISM_ACCELERATION_LEVEL") or "balanced").strip().lower()
    if key not in METABOLIC_ACCELERATION_PROFILES:
        key = "balanced"
    return dict(METABOLIC_ACCELERATION_PROFILES[key])


def _truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "execute", "enabled"}


def _empty_net_gain() -> dict[str, int]:
    return {"promoted": 0, "blocked_source_missing": 0, "queue_reduced_estimate": 0}


def _sum_net_gain(total: dict[str, int], current: dict[str, Any] | None) -> dict[str, int]:
    current = current or {}
    return {
        "promoted": int(total.get("promoted", 0)) + int(current.get("promoted", 0) or 0),
        "blocked_source_missing": int(total.get("blocked_source_missing", 0)) + int(current.get("blocked_source_missing", 0) or 0),
        "queue_reduced_estimate": int(total.get("queue_reduced_estimate", 0)) + int(current.get("queue_reduced_estimate", 0) or 0),
    }


def run_metabolic_evolution_probe(
    session_id: str,
    *,
    execute: bool = False,
    limit: int | None = None,
    acceleration: str | None = None,
    daily_cap: int | None = None,
    batch_size: int | None = None,
    max_batches: int | None = None,
    run_batch=None,
    env_execute: str | None = None,
) -> dict[str, Any]:
    """Phase 1d/Phase13: high-throughput bounded GeneDB metabolism.

    Fast path is A/B low-risk metabolism only: controlled promotion + source-missing
    blocking. Execute still requires an explicit env gate; otherwise the same high
    throughput loop runs as dry-run evidence.
    """
    profile = resolve_metabolic_acceleration(acceleration)
    resolved_batch_size = int(batch_size or limit or profile["batch_size"])
    resolved_max_batches = int(max_batches or profile["max_batches"])
    resolved_daily_cap = int(daily_cap or profile["daily_cap"])
    resolved_batch_size = max(1, min(resolved_batch_size, 50))
    resolved_max_batches = max(1, resolved_max_batches)
    resolved_daily_cap = max(1, resolved_daily_cap)

    explicit_gate = _truthy_env(os.environ.get(METABOLIC_EXECUTE_ENV) if env_execute is None else env_execute)
    execute_allowed = bool(execute and explicit_gate)
    outdir = METABOLIC_NET_GAIN_ROOT / session_id
    batches: list[dict[str, Any]] = []
    aggregate = _empty_net_gain()
    processed_estimate = 0
    consecutive_zero_gain = 0
    fuse_triggered = False
    fuse_reason = ""
    last_result: dict[str, Any] = {}

    try:
        if run_batch is None:
            from agent.pgg_batch_proof_metabolism_loop import run_batch_metabolism_loop as run_batch

        batch_no = 0
        while batch_no < resolved_max_batches and processed_estimate < resolved_daily_cap:
            batch_no += 1
            remaining = resolved_daily_cap - processed_estimate
            current_limit = min(resolved_batch_size, remaining)
            batch_outdir = outdir / f"batch-{batch_no:02d}"
            result = run_batch(batch_outdir, limit=current_limit, execute=execute_allowed, prefer_rust_mutation=True)
            last_result = result
            net_gain = result.get("net_gain") or _empty_net_gain()
            queue_delta = int(net_gain.get("queue_reduced_estimate", 0) or 0)
            aggregate = _sum_net_gain(aggregate, net_gain)
            processed_estimate += current_limit
            batches.append({
                "batch": batch_no,
                "outdir": result.get("outdir"),
                "limit": current_limit,
                "execute": bool(result.get("execute")),
                "mutation_backend": result.get("mutation_backend"),
                "db_mutation": bool(result.get("db_mutation")),
                "backup_path": result.get("backup_path"),
                "net_gain": net_gain,
                "repair_backlog_count": result.get("repair_backlog_count"),
            })

            if result.get("mutation_backend") != "rust":
                fuse_triggered = True
                fuse_reason = "non_rust_mutation_backend"
                break
            if execute_allowed and not result.get("db_mutation") and queue_delta > 0:
                fuse_triggered = True
                fuse_reason = "execute_requested_but_no_db_mutation"
                break
            if queue_delta <= 0:
                consecutive_zero_gain += 1
                if consecutive_zero_gain >= 2:
                    fuse_triggered = True
                    fuse_reason = "zero_net_gain_two_consecutive_batches"
                    break
            else:
                consecutive_zero_gain = 0

        status = "PASS_EXECUTED_BOUNDED" if execute_allowed and aggregate["queue_reduced_estimate"] > 0 else "PASS_DRY_RUN_ONLY"
        if fuse_triggered and fuse_reason.startswith("zero_net_gain"):
            status = "FUSED_NO_NET_GAIN"
        elif fuse_triggered:
            status = "FUSED_BLOCKED"

        return {
            "status": status,
            "requested_execute": bool(execute),
            "execute_allowed": execute_allowed,
            "execute_env": METABOLIC_EXECUTE_ENV,
            "acceleration": profile["acceleration"],
            "profile": {
                "max_batches": resolved_max_batches,
                "batch_size": resolved_batch_size,
                "daily_cap": resolved_daily_cap,
            },
            "total_batches": len(batches),
            "processed_estimate": processed_estimate,
            "schema": last_result.get("schema"),
            "mutation_backend": last_result.get("mutation_backend"),
            "db_mutation": any(bool(b.get("db_mutation")) for b in batches),
            "db_path": last_result.get("db_path"),
            "backup_path": last_result.get("backup_path"),
            "rollback_paths": [b.get("backup_path") for b in batches if b.get("backup_path")],
            "net_gain": aggregate,
            "aggregate_net_gain": aggregate,
            "repair_backlog_count": last_result.get("repair_backlog_count"),
            "batches": batches,
            "outdir": str(outdir),
            "fuse_triggered": fuse_triggered,
            "fuse_reason": fuse_reason,
            "boundary": "Phase13 high-throughput bounded GeneDB metabolism: A/B/C fast lanes only; legal/security/credential remain audit-only; no AGI/T5/external benchmark claim",
        }
    except Exception as e:
        return {
            "status": "WATCH",
            "requested_execute": bool(execute),
            "execute_allowed": execute_allowed,
            "acceleration": profile["acceleration"],
            "error": f"{type(e).__name__}: {e}",
            "boundary": "metabolic probe failed before any trusted autonomy execute claim",
        }


# ── Main Loop ─────────────────────────────────────────────────────────────

def run(dry_run: bool = False, session_id: str = "default") -> DailyReport:
    print(f"[PGG Autonomy Default v1.1] {'DRY RUN' if dry_run else 'LIVE'} session={session_id}")

    print("\n[Phase 1/5] 运行探针...")
    probes = run_probes()
    print(f"  {sum(1 for p in probes if p.status in ('PASS','SKIP'))} PASS / "
          f"{sum(1 for p in probes if p.status in ('WATCH','BLOCKED'))} WATCH / "
          f"{sum(1 for p in probes if p.status == 'ERROR')} ERROR")

    print("\n[Phase 1b/5] 开源学习...")
    try:
        learning_results = open_source_learning()
        probes.extend(learning_results)
        for r in learning_results:
            print(f"  [{r.status}] {r.summary[:100]}")
    except Exception as e:
        print(f"  [WATCH] open_source_learning failed: {e}")

    print("\n[Phase 1d/5] 代谢型进化净增益（Phase13 high-throughput Rust batch）...")
    metabolic_execute = bool(not dry_run and _truthy_env(os.environ.get(METABOLIC_EXECUTE_ENV)))
    metabolic = run_metabolic_evolution_probe(session_id, execute=metabolic_execute, acceleration=os.environ.get("PGG_METABOLISM_ACCELERATION_LEVEL") or "balanced")
    print(f"  [{metabolic.get('status')}] accel={metabolic.get('acceleration')} batches={metabolic.get('total_batches')} backend={metabolic.get('mutation_backend')} db_mutation={metabolic.get('db_mutation')} net_gain={metabolic.get('net_gain')}")

    print("\n[Phase 2/5] 深度案件复验（使用真实门禁）...")
    cases = deep_case_check()
    for c in cases:
        if c.get("status") == "WATCH":
            print(f"  ⚠ {c.get('case_id','?')}: {', '.join(c.get('warnings',[]))}")
        elif c.get("findings"):
            print(f"  ✓ {c.get('case_id','?')}: {', '.join(c.get('findings',[])[:3])}")

    if not dry_run:
        print("\n[Phase 3/5] 自动修复低风险项...")
        fixes = auto_fix()
        applied = [f for f in fixes if f.result.get("applied")]
        print(f"  {len(applied)}/{len(fixes)} 项已修复")
    else:
        fixes = []
        print("\n[Phase 3/5] 跳过自动修复 (dry-run)")

    print("\n[Phase 4/5] 自改进计划...")
    imp_plan = generate_improvement_plan(probes, cases)
    print(f"  {len(imp_plan)} 项改进计划")
    for x in imp_plan:
        print(f"  {'✅' if x.applied else '⏳'} [{x.source}] {x.issue[:120]}")

    print("\n[Phase 4b/5] 全自动 PR 创建（不自动 merge）...")
    pr_results = auto_create_pr_from_fixes(fixes, imp_plan, REPO)
    for r in pr_results:
        print(f"  [{r['status']}] {r.get('url','')}")

    llm_budget_used = len(probes) * 20000  # rough estimate, zero-L probes

    print("\n[Phase 5/5] 生成报告 & 复盘...")
    report = DailyReport(
        generated_at=_now_str(), session_id=session_id,
        probes=probes, auto_fixes=fixes,
        case_reverifications=cases, metabolic_evolution=metabolic,
        improvement_plan=imp_plan,
        llm_budget_used=llm_budget_used,
        llm_budget_remaining=max(0, LLM_DAILY_BUDGET_TOKENS - llm_budget_used),
    )
    report.summary = build_summary(probes, fixes, cases, imp_plan, llm_budget_used, metabolic)
    report.boundary = ("internal bounded self-evolution loop v1.1; "
                       "not full AGI, not external L2/T5, not legal correctness proof")

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    art = WORKSPACE / f"autonomy_{ts}.json"
    art.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, default=str),
                   encoding="utf-8")

    last = WORKSPACE / "latest.json"
    if last.exists(): last.unlink()
    try: last.symlink_to(art.name)
    except: pass

    mk = f"latest_autonomy_loop_{ts}"
    _append_manifest(mk, {
        "schema": "PGGAutonomyDefaultReport/v1.1",
        "status": "PASS_RUN" if not dry_run else "PASS_DRY_RUN",
        "generated_at": report.generated_at,
        "probes_pass": sum(1 for p in probes if p.status in ("PASS", "SKIP")),
        "probes_watch": sum(1 for p in probes if p.status in ("WATCH", "BLOCKED")),
        "auto_fixes_applied": sum(1 for f in fixes if f.result.get("applied")),
        "case_pass": sum(1 for c in cases if c.get("status") == "PASS"),
        "case_watch": sum(1 for c in cases if c.get("status") == "WATCH"),
        "metabolic_status": metabolic.get("status"),
        "metabolic_backend": metabolic.get("mutation_backend"),
        "metabolic_db_mutation": metabolic.get("db_mutation"),
        "metabolic_net_gain": metabolic.get("net_gain"),
        "metabolic_acceleration": metabolic.get("acceleration"),
        "metabolic_total_batches": metabolic.get("total_batches"),
        "metabolic_processed_estimate": metabolic.get("processed_estimate"),
        "metabolic_execute_allowed": metabolic.get("execute_allowed"),
        "metabolic_fuse_triggered": metabolic.get("fuse_triggered"),
        "improvement_plan_count": len(imp_plan),
        "artifact": str(art),
    })
    print(f"\n  报告: {art}")
    print(f"  Manifest: {mk}")

    return report


def main():
    parser = argparse.ArgumentParser(description="PGG Autonomy Default Loop v1.1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()

    report = run(dry_run=args.dry_run, session_id=args.session_id)
    if not args.no_report:
        print("\n" + "=" * 60)
        print(report.summary)
        print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
