"""PGG Autonomy Controller v0.1/v0.2/v0.3/v0.4/v0.6.

Bounded autonomous control plane for Apple Didi / PGG Archon.

This module is intentionally conservative:
- status/plan/step proposal are read-only by default;
- it may run local read-only probes (git status, health CLIs, audit summaries);
- v0.3 adds safe-check execution for py_compile / focused pytest / npm audit / cargo audit reads;
- v0.4 adds a read-only observation loop artifact: latest JSON/MD, append-only ledger, anomaly summary;
- v0.6 adds compact heartbeat / P0 alert output for launchd LIGHT logs;
- v0.7 adds read-only P0 triage action packets; suggestions only, no apply;
- v0.8 adds read-only dry-run patch/command packets for low-risk P0s; no apply;
- it does not mutate credentials, provider config, scheduler/security boundary,
  legal case finalization, production answer-chain switches, or memory files;
- generated steps are proposals unless a future explicit executor gate approves them.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

# ── Rust native bridge ──────────────────────────────────────────
_NATIVE = False
try:
    import hermes_pgg_autonomy_core as _rust_ac
    _NATIVE = True
except ImportError:
    _rust_ac = None

def _rust_bridge(func_name: str, *args) -> Any:
    if not _NATIVE:
        raise RuntimeError(f"Rust native not available for {func_name}")
    fn = getattr(_rust_ac, func_name, None)
    if fn is None:
        raise RuntimeError(f"Missing Rust function: {func_name}")
    raw = fn(*args)
    return json.loads(raw) if raw and raw[0] in ('{', '[') else raw
# ────────────────────────────────────────────────────────────────

HOME = Path.home()
HERMES_HOME = HOME / ".hermes"
REPO = HERMES_HOME / "hermes-agent"
MANIFEST = HERMES_HOME / "data" / "EVOLUTION_MANIFEST.json"
WORKSPACE = HERMES_HOME / "workspace" / "pgg-archon-governance" / "autonomy-controller"

P0_KEYWORDS = ("SyntaxError", "py_compile", "credential", "secret", "CRITICAL", "critical", "dirty_repo", "memory_watch")
HARD_BOUNDARIES = [
    "no_credential_mutation",
    "no_provider_config_mutation",
    "no_scheduler_security_mutation",
    "no_production_answer_chain_switch",
    "no_legal_finalization",
    "no_cross_profile_write",
    "no_memory_apply_without_backup",
]


@dataclass
class Probe:
    name: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacklogItem:
    id: str
    priority: str
    title: str
    reason: str
    evidence: list[str]
    proposed_next_step: str
    risk: str = "LOW"
    allowed_auto_action: bool = False
    blocked_by: list[str] = field(default_factory=list)


@dataclass
class DirtyFileClassification:
    raw: str
    path: str
    git_status: str
    category: str
    risk: str
    owner_hint: str
    safe_checks: list[str]
    recommended_action: str


@dataclass
class SafeCheckResult:
    name: str
    status: str
    command: str
    scope: str
    rc: int
    output_preview: str
    skipped_reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutonomyStatus:
    schema: str
    generated_at_epoch: float
    boundary: str
    mode: str
    probes: list[Probe]
    backlog: list[BacklogItem]
    summary: dict[str, Any]
    hard_boundaries: list[str]


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 30) -> dict[str, Any]:
    try:
        cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return {"rc": cp.returncode, "output": cp.stdout[-12000:]}
    except FileNotFoundError as exc:
        return {"rc": 127, "output": f"FileNotFoundError: {exc}"}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "output": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "TIMEOUT"}
    except Exception as exc:  # pragma: no cover - defensive surface
        return {"rc": 1, "output": f"{type(exc).__name__}: {exc}"}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def classify_dirty_line(line: str) -> DirtyFileClassification:
    """Classify a `git status --short` line without mutating the repo."""
    if _NATIVE:
        raw_str = _rust_bridge("native_classify_dirty_line", line)
        return DirtyFileClassification(**raw_str)
    raw = line.rstrip("\n")
    git_status = raw[:2].strip() or "??"
    path = raw[3:].strip() if len(raw) > 3 else raw.strip()
    safe_checks: list[str] = []
    category = "unknown_dirty"
    risk = "MEDIUM_REVIEW_REQUIRED"
    owner_hint = "unknown_or_foreign_session"
    recommended = "Inspect scoped diff before any add/commit/revert."

    if path in {"agent/pgg_archon_autonomy_controller.py", "tests/test_pgg_archon_autonomy_controller.py"}:
        category = "current_autonomy_controller"
        risk = "LOW_CURRENT_TASK"
        owner_hint = "current_session"
        recommended = "Run py_compile/pytest, then scoped commit if clean."
    elif path in {
        "agent/pgg_archon_external_benchmark_provider_run.py",
        "agent/pgg_archon_quantum_channel_router.py",
        "hermes_cli/web_server.py",
    }:
        category = "omniroute_provider_trace_or_status"
        risk = "LOW_TO_MEDIUM_FOREIGN_SESSION"
        owner_hint = "likely_other_session_or_adjacent_omniroute_work"
        recommended = "Do not mix into autonomy commit; run focused diff/tests in separate batch."
    elif path.endswith("package-lock.json") or path.endswith("Cargo.lock"):
        category = "lockfile_supply_chain"
        risk = "LOW_TO_MEDIUM_LOCKFILE"
        owner_hint = "dependency_governance"
        recommended = "Run scoped audit/build tests before commit."
    elif path.endswith(".py"):
        category = "python_code"
        risk = "MEDIUM_CODE"
        owner_hint = "unknown_python_change"
        recommended = "Run py_compile and focused pytest before commit."
    elif "/target/" in path or path.endswith(".pyc") or "__pycache__" in path:
        category = "generated_artifact"
        risk = "LOW_SHOULD_IGNORE_OR_REMOVE"
        owner_hint = "generated"
        recommended = "Do not commit; remove or add ignore rule if appropriate."

    if path.endswith(".py"):
        safe_checks.append(f"py_compile:{path}")
    if path.startswith("tests/") and path.endswith(".py"):
        safe_checks.append(f"pytest:{path}")
    if path.endswith("package-lock.json"):
        safe_checks.append("npm_audit_scope")
    if path.endswith("Cargo.lock") or path.endswith("Cargo.toml"):
        safe_checks.append("cargo_test_or_audit_scope")

    return DirtyFileClassification(raw, path, git_status, category, risk, owner_hint, safe_checks, recommended)


def classify_dirty_lines(lines: list[str]) -> list[DirtyFileClassification]:
    if _NATIVE:
        raw = _rust_bridge("native_classify_dirty_lines", lines)
        return [DirtyFileClassification(**item) for item in raw]
    return [classify_dirty_line(line) for line in lines if line.strip()]


def dirty_summary(classifications: list[DirtyFileClassification]) -> dict[str, Any]:
    if _NATIVE:
        return _rust_bridge("native_dirty_summary", json.dumps([asdict(c) for c in classifications], ensure_ascii=False))
    by_category: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for item in classifications:
        by_category[item.category] = by_category.get(item.category, 0) + 1
        by_risk[item.risk] = by_risk.get(item.risk, 0) + 1
    return {
        "count": len(classifications),
        "by_category": by_category,
        "by_risk": by_risk,
        "items": [asdict(x) for x in classifications[:50]],
    }


def dirty_priority(classifications: list[DirtyFileClassification]) -> str:
    """Classify dirty worktree priority without over-claiming foreign-session files."""
    if _NATIVE:
        return _rust_bridge("native_dirty_priority", json.dumps([asdict(c) for c in classifications], ensure_ascii=False))
    if not classifications:
        return "PASS"
    p0_risks = {"LOW_CURRENT_TASK", "HIGH_CREDENTIAL", "HIGH_SECURITY"}
    if any(item.risk in p0_risks or item.owner_hint == "current_session" for item in classifications):
        return "P0"
    return "P1"


def probe_git() -> Probe:
    res = _run(["git", "status", "--short"], cwd=REPO, timeout=20)
    lines = [ln for ln in res["output"].splitlines() if ln.strip()]
    classifications = classify_dirty_lines(lines[:50])
    priority = dirty_priority(classifications)
    if res["rc"] == 0 and not lines:
        status = "PASS_CLEAN"
    elif priority == "P0":
        status = "WATCH_DIRTY_P0_CURRENT_TASK"
    else:
        status = "WATCH_DIRTY_P1_FOREIGN_OR_GENERATED"
    return Probe(
        "git_status",
        status,
        f"dirty_lines={len(lines)}",
        {"rc": res["rc"], "lines": lines[:50], "classification": dirty_summary(classifications), "dirty_priority": priority},
    )


def probe_memory() -> Probe:
    cli = HERMES_HOME / "bin" / "memory_runtime_health"
    res = _run([str(cli)], timeout=40) if cli.exists() else {"rc": 127, "output": "missing memory_runtime_health"}
    first = res["output"].splitlines()[0] if res["output"].splitlines() else ""
    status = "PASS" if "memory_runtime_health: PASS" in res["output"] else "WATCH"
    return Probe("memory_runtime_health", status, first, {"rc": res["rc"], "output_preview": res["output"][:2000]})


def probe_system_map() -> Probe:
    cli = HERMES_HOME / "bin" / "pgg_system_map_status"
    res = _run([str(cli)], timeout=50) if cli.exists() else {"rc": 127, "output": "missing pgg_system_map_status"}
    data = None
    try:
        data = json.loads(res["output"])
    except Exception:
        pass
    status = "PASS" if res["rc"] == 0 and isinstance(data, dict) else "WATCH"
    return Probe("system_map", status, "pgg_system_map_status read", {"rc": res["rc"], "data": data or res["output"][:2000]})


def probe_skillflow() -> Probe:
    cli = HERMES_HOME / "bin" / "pgg_skillflow_readiness"
    res = _run([str(cli)], timeout=40) if cli.exists() else {"rc": 127, "output": "missing pgg_skillflow_readiness"}
    out = res["output"].strip()
    status = "HOLD" if "HOLD" in out else ("PASS" if "PASS" in out else "WATCH")
    return Probe("skillflow_readiness", status, out[:500], {"rc": res["rc"], "output_preview": out[:2000]})


def probe_root_npm_audit() -> Probe:
    if not (REPO / "package-lock.json").exists():
        return Probe("root_npm_audit", "SKIP", "no package-lock.json", {})
    res = _run(["npm", "audit", "--json"], cwd=REPO, timeout=80)
    data = None
    try:
        data = json.loads(res["output"])
    except Exception:
        pass
    vulns = (((data or {}).get("metadata") or {}).get("vulnerabilities") or {}) if isinstance(data, dict) else {}
    total = int(vulns.get("total") or 0) if isinstance(vulns, dict) else -1
    status = "PASS" if total == 0 else "WATCH"
    return Probe("root_npm_audit", status, f"total_vulnerabilities={total}", {"rc": res["rc"], "vulnerabilities": vulns})


def probe_manifest() -> Probe:
    data = _read_json(MANIFEST)
    if not isinstance(data, dict):
        return Probe("manifest", "WATCH", "manifest unreadable", {"path": str(MANIFEST)})
    latest = sorted([k for k in data if k.startswith("latest_")])[-20:]
    return Probe("manifest", "PASS", f"latest_keys_sample={len(latest)}", {"path": str(MANIFEST), "latest_tail": latest})


@dataclass
class SafeCheckPlanItem:
    name: str
    command: list[str]
    cwd: str | None
    scope: str
    reason: str


def collect_probes(*, include_audit: bool = True) -> list[Probe]:
    probes = [probe_git(), probe_memory(), probe_system_map(), probe_skillflow(), probe_manifest()]
    if include_audit:
        probes.append(probe_root_npm_audit())
    return probes


def _safe_check_plan_from_git(probe: Probe) -> list[SafeCheckPlanItem]:
    lines = probe.details.get("lines", []) if probe else []
    classifications = classify_dirty_lines(lines[:50])
    plan: list[SafeCheckPlanItem] = []
    seen: set[tuple[str, tuple[str, ...], str | None]] = set()

    def add(name: str, command: list[str], cwd: str | None, scope: str, reason: str) -> None:
        key = (name, tuple(command), cwd)
        if key in seen:
            return
        seen.add(key)
        plan.append(SafeCheckPlanItem(name=name, command=command, cwd=cwd, scope=scope, reason=reason))

    for item in classifications:
        rel_path = item.path
        abs_path = str((REPO / rel_path).resolve())
        if item.path.endswith(".py") and (REPO / rel_path).exists():
            add(
                name=f"py_compile:{rel_path}",
                command=[sys.executable, "-m", "py_compile", abs_path],
                cwd=str(REPO),
                scope=item.category,
                reason=item.recommended_action,
            )
        if rel_path.startswith("tests/") and rel_path.endswith(".py") and (REPO / rel_path).exists():
            add(
                name=f"pytest:{rel_path}",
                command=[sys.executable, "-m", "pytest", "-q", abs_path],
                cwd=str(REPO),
                scope=item.category,
                reason=item.recommended_action,
            )
        if rel_path.endswith("package-lock.json") and (REPO / rel_path).exists():
            add(
                name="npm_audit:read",
                command=["npm", "audit", "--json"],
                cwd=str(REPO),
                scope="lockfile_supply_chain",
                reason="read-only npm audit for lockfile supply-chain hygiene",
            )
        if (rel_path.endswith("Cargo.lock") or rel_path.endswith("Cargo.toml")) and (REPO / rel_path).exists():
            add(
                name="cargo_audit:read",
                command=["cargo", "audit", "--json"],
                cwd=str(REPO),
                scope="rust_supply_chain",
                reason="read-only cargo audit for Rust dependency hygiene",
            )
    return plan


def execute_safe_checks(plan: list[SafeCheckPlanItem]) -> list[SafeCheckResult]:
    results: list[SafeCheckResult] = []
    for item in plan:
        if not item.command:
            results.append(SafeCheckResult(item.name, "SKIP", "", item.scope, 0, "", "empty_command", {"reason": item.reason}))
            continue
        if item.command[0] == "cargo" and shutil.which("cargo") is None:
            results.append(SafeCheckResult(item.name, "SKIP", " ".join(item.command), item.scope, 127, "cargo missing", "cargo_not_installed", {"reason": item.reason}))
            continue
        if item.command[0] == "npm" and shutil.which("npm") is None:
            results.append(SafeCheckResult(item.name, "SKIP", " ".join(item.command), item.scope, 127, "npm missing", "npm_not_installed", {"reason": item.reason}))
            continue
        res = _run(item.command, cwd=Path(item.cwd) if item.cwd else None, timeout=180)
        output = res["output"]
        status = "PASS" if res["rc"] == 0 else "WATCH"
        if item.name.startswith("npm_audit"):
            try:
                payload = json.loads(output)
                vulns = (((payload or {}).get("metadata") or {}).get("vulnerabilities") or {})
                total = int(vulns.get("total") or 0)
                status = "PASS" if total == 0 else "WATCH"
                results.append(SafeCheckResult(item.name, status, " ".join(item.command), item.scope, res["rc"], output[:2000], details={"vulnerabilities": vulns, "reason": item.reason}))
                continue
            except Exception:
                status = "WATCH"
        if item.name.startswith("cargo_audit") and res["rc"] == 127:
            status = "SKIP"
        results.append(SafeCheckResult(item.name, status, " ".join(item.command), item.scope, res["rc"], output[:2000], details={"reason": item.reason}))
    return results


def safe_check_summary(results: list[SafeCheckResult]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in results:
        counts[item.status] = counts.get(item.status, 0) + 1
    return {
        "count": len(results),
        "status_counts": counts,
        "items": [asdict(x) for x in results[:50]],
    }


def _safe_checks_enabled() -> bool:
    flag = os.environ.get("PGG_AUTONOMY_SAFE_CHECKS", "1").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return True


def backlog_from_probes(probes: list[Probe]) -> list[BacklogItem]:
    if _NATIVE:
        raw = _rust_bridge("native_backlog_from_probes", json.dumps([asdict(p) for p in probes], ensure_ascii=False))
        return [BacklogItem(**item) for item in raw]
    items: list[BacklogItem] = []
    by_name = {p.name: p for p in probes}

    git = by_name.get("git_status")
    if git and git.status != "PASS_CLEAN":
        lines = git.details.get("lines", [])
        classification = git.details.get("classification") or {}
        category_bits = [f"category:{k}={v}" for k, v in (classification.get("by_category") or {}).items()]
        priority = "P0" if git.details.get("dirty_priority") == "P0" else "P1"
        items.append(BacklogItem(
            id=f"{priority}_dirty_repo_classify",
            priority=priority,
            title="Classify dirty repository changes before further autonomous writes",
            reason="dirty worktree can contaminate future commits and completion claims",
            evidence=[git.summary, *category_bits, *[str(x) for x in lines[:8]]],
            proposed_next_step="Use dirty classification to separate current_task vs foreign_session; run safe_checks only, then scoped commit/quarantine in separate batches.",
            risk="LOW_READ_ONLY",
            allowed_auto_action=True,
        ))

    mem = by_name.get("memory_runtime_health")
    if mem and mem.status != "PASS":
        items.append(BacklogItem(
            id="P0_memory_health_watch",
            priority="P0",
            title="Restore prompt memory health with backup-preserving compaction",
            reason="memory health WATCH risks prompt drift or oversized injected context",
            evidence=[mem.summary],
            proposed_next_step="Create preimage archive, merge duplicate USER/MEMORY entries only, run memory_runtime_health readback.",
            risk="MEDIUM_MEMORY_WRITE",
            allowed_auto_action=False,
            blocked_by=["requires backup and explicit memory-write gate"],
        ))

    npm = by_name.get("root_npm_audit")
    if npm and npm.status == "WATCH":
        vulns = npm.details.get("vulnerabilities", {})
        items.append(BacklogItem(
            id="P1_root_npm_audit_watch",
            priority="P1",
            title="Triage root npm audit vulnerabilities",
            reason="supply-chain vulnerabilities remain in lockfile",
            evidence=[json.dumps(vulns, ensure_ascii=False)],
            proposed_next_step="Run scoped npm audit detail; prefer package-lock-only minimal update; build/test before commit.",
            risk="LOW_TO_MEDIUM_LOCKFILE",
            allowed_auto_action=True,
        ))

    sf = by_name.get("skillflow_readiness")
    if sf and sf.status == "HOLD":
        items.append(BacklogItem(
            id="P1_skillflow_hold_truth_boundary",
            priority="P1",
            title="Keep SkillFlow in HOLD until corrected live evidence exists",
            reason="user flagged real_live counters as possibly fabricated/drifted",
            evidence=[sf.summary],
            proposed_next_step="Read corrected readiness ledgers only; do not promote route_enforce or production answer-chain.",
            risk="LOW_READ_ONLY",
            allowed_auto_action=True,
        ))

    sm = by_name.get("system_map")
    if sm and sm.status != "PASS":
        items.append(BacklogItem(
            id="P1_system_map_unavailable",
            priority="P1",
            title="Repair or regenerate pgg_system_map_status read-only entrypoint",
            reason="autonomy controller depends on stable system map status",
            evidence=[sm.summary],
            proposed_next_step="Inspect CLI path, run py_compile, restore from manifest report if needed.",
            risk="LOW_TO_MEDIUM_CODE_FIX",
            allowed_auto_action=True,
        ))

    if not items:
        items.append(BacklogItem(
            id="P2_autonomy_observation_loop",
            priority="P2",
            title="Enable periodic read-only autonomy planning observation",
            reason="no P0/P1 blockers detected; next autonomy gap is cross-session proactive planning",
            evidence=["all core probes PASS/HOLD-expected"],
            proposed_next_step="Create low-frequency read-only launchd/LIGHT plan runner after one more manual observation cycle.",
            risk="MEDIUM_SCHEDULER_WRITE",
            allowed_auto_action=False,
            blocked_by=["scheduler/launchd write requires explicit scoped landing gate"],
        ))

    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return sorted(items, key=lambda x: (priority_order.get(x.priority, 9), x.id))


def build_status(*, include_audit: bool = True, mode: str = "status") -> AutonomyStatus:
    probes = collect_probes(include_audit=include_audit)
    backlog = backlog_from_probes(probes)
    counts: dict[str, int] = {}
    for item in backlog:
        counts[item.priority] = counts.get(item.priority, 0) + 1
    git_probe = next((p for p in probes if p.name == "git_status"), None)
    safe_check_plan = _safe_check_plan_from_git(git_probe) if git_probe else []
    safe_check_results = execute_safe_checks(safe_check_plan) if _safe_checks_enabled() else []
    safe_summary = safe_check_summary(safe_check_results)
    return AutonomyStatus(
        schema="PGGAutonomyController/v0.8",
        generated_at_epoch=time.time(),
        boundary="bounded autonomous planner: read-only sensing, proposal generation, read-only safe-check execution, observation ledger, and compact P0 alert heartbeat; no high-risk mutation or production switch",
        mode=mode,
        probes=probes,
        backlog=backlog,
        summary={
            "probe_count": len(probes),
            "backlog_count": len(backlog),
            "priority_counts": counts,
            "next_item": asdict(backlog[0]) if backlog else None,
            "autonomy_level": "bounded_proactive_observer_v0.8_with_dry_run_patch_packet",
            "safe_check_plan_count": len(safe_check_plan),
            "safe_check_summary": safe_summary,
            "safe_checks_executed": _safe_checks_enabled(),
        },
        hard_boundaries=HARD_BOUNDARIES,
    )


def anomaly_summary(status: AutonomyStatus) -> dict[str, Any]:
    """Return compact observation anomalies without mutating anything."""
    anomalies: list[dict[str, Any]] = []
    for probe in status.probes:
        if probe.status.startswith("WATCH"):
            if probe.name == "memory_runtime_health":
                severity = "P0"
            elif probe.name == "git_status":
                severity = "P0" if probe.details.get("dirty_priority") == "P0" else "P1"
            else:
                severity = "P1"
            anomalies.append({
                "id": f"{severity}_{probe.name}",
                "severity": severity,
                "source": probe.name,
                "status": probe.status,
                "summary": probe.summary,
                "boundary": "read_only_observation_no_mutation",
            })
    for item in status.backlog:
        if item.priority in {"P0", "P1"}:
            anomalies.append({
                "id": item.id,
                "severity": item.priority,
                "source": "backlog",
                "status": "OPEN",
                "summary": item.title,
                "allowed_auto_action": item.allowed_auto_action,
                "blocked_by": item.blocked_by,
                "boundary": "backlog_item_only_no_mutation",
            })
    severity_counts: dict[str, int] = {}
    for item in anomalies:
        sev = str(item.get("severity") or "UNKNOWN")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    return {
        "schema": "PGGAutonomyAnomalySummary/v0.4",
        "status": "PASS_NO_P0" if not any(x.get("severity") == "P0" for x in anomalies) else "WATCH_P0_PRESENT",
        "count": len(anomalies),
        "severity_counts": severity_counts,
        "items": anomalies[:50],
        "boundary": "read-only anomaly summary; does not execute fixes or mutate scheduler/security/provider/credentials",
    }


def write_latest(status: AutonomyStatus) -> dict[str, str]:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    data = asdict(status)
    latest_json = WORKSPACE / "pgg_autonomy_latest.json"
    latest_md = WORKSPACE / "pgg_autonomy_latest.md"
    ledger = WORKSPACE / "pgg_autonomy_ledger.jsonl"
    latest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_md.write_text("# PGG Autonomy Controller Latest\n\n```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    return {"latest_json": str(latest_json), "latest_md": str(latest_md), "ledger": str(ledger)}


def write_observation(status: AutonomyStatus) -> dict[str, str]:
    """Write v0.4 read-only observation artifacts and append ledger."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    data = {**asdict(status), "anomaly_summary": anomaly_summary(status)}
    latest_json = WORKSPACE / "pgg_autonomy_observation_latest.json"
    latest_md = WORKSPACE / "pgg_autonomy_observation_latest.md"
    ledger = WORKSPACE / "pgg_autonomy_observation_ledger.jsonl"
    latest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_md.write_text(
        "# PGG Autonomy Observation Latest\n\n"
        f"- schema: {data.get('schema')}\n"
        f"- anomaly_status: {data['anomaly_summary'].get('status')}\n"
        f"- anomaly_count: {data['anomaly_summary'].get('count')}\n"
        f"- boundary: {data['anomaly_summary'].get('boundary')}\n\n"
        "```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    return {"observation_json": str(latest_json), "observation_md": str(latest_md), "observation_ledger": str(ledger)}


def build_p0_triage_packet(status: AutonomyStatus, paths: dict[str, str] | None = None) -> dict[str, Any]:
    """Build read-only P0 triage action packet; never applies changes."""
    summary = anomaly_summary(status)
    p0_items = [x for x in summary.get("items", []) if x.get("severity") == "P0"]
    actions: list[dict[str, Any]] = []
    by_probe = {p.name: p for p in status.probes}
    git_probe = by_probe.get("git_status")
    if git_probe and git_probe.status == "WATCH_DIRTY":
        classification = (git_probe.details or {}).get("classification") or {}
        actions.append({
            "id": "triage_dirty_worktree",
            "risk": "LOW_READ_ONLY",
            "source": "git_status",
            "suggested_checks": ["git status --short", "git diff --stat", "run generated safe_checks"],
            "suggested_actions": [
                "Separate current-task files from foreign-session files.",
                "Commit only scoped verified files, or leave untracked/foreign files untouched.",
                "Do not auto-revert without explicit user authorization.",
            ],
            "evidence": classification,
            "apply_allowed": False,
        })
    mem_probe = by_probe.get("memory_runtime_health")
    if mem_probe and mem_probe.status == "WATCH":
        actions.append({
            "id": "triage_memory_watch",
            "risk": "MEDIUM_MEMORY_WRITE_REQUIRES_BACKUP",
            "source": "memory_runtime_health",
            "suggested_checks": ["memory_runtime_health", "wc -c USER.md MEMORY.md SOUL.md"],
            "suggested_actions": [
                "Create preimage archive before any memory edit.",
                "Compact only duplicate/low-signal USER/MEMORY entries.",
                "Rerun memory_runtime_health and record readback.",
            ],
            "evidence": mem_probe.details,
            "apply_allowed": False,
        })
    return {
        "schema": "PGGAutonomyP0TriagePacket/v0.7",
        "status": "TRIAGE_P0_READY" if p0_items else "NO_P0_TRIAGE_NEEDED",
        "generated_at_epoch": status.generated_at_epoch,
        "p0_count": len(p0_items),
        "p0_items": p0_items[:10],
        "actions": actions,
        "artifact_paths": paths or {},
        "boundary": "read-only triage packet; suggestions only; no apply, no commit, no provider/config/scheduler/security/production/legal mutation",
    }


def write_triage_packet(status: AutonomyStatus, paths: dict[str, str] | None = None) -> dict[str, str]:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    packet = build_p0_triage_packet(status, paths)
    latest_json = WORKSPACE / "pgg_autonomy_p0_triage_latest.json"
    latest_md = WORKSPACE / "pgg_autonomy_p0_triage_latest.md"
    ledger = WORKSPACE / "pgg_autonomy_p0_triage_ledger.jsonl"
    latest_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_md.write_text("# PGG Autonomy P0 Triage Packet\n\n```json\n" + json.dumps(packet, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(packet, ensure_ascii=False, sort_keys=True) + "\n")
    return {"triage_json": str(latest_json), "triage_md": str(latest_md), "triage_ledger": str(ledger)}


def build_dry_run_packet(status: AutonomyStatus, triage_packet: dict[str, Any] | None = None, paths: dict[str, str] | None = None) -> dict[str, Any]:
    """Build review-only dry-run patch/command packet; never applies changes."""
    triage_packet = triage_packet or build_p0_triage_packet(status, paths)
    commands: list[dict[str, Any]] = []
    patch_drafts: list[dict[str, Any]] = []
    for action in triage_packet.get("actions", []):
        if action.get("id") == "triage_memory_watch":
            commands.extend([
                {"purpose": "preimage_backup", "command": "mkdir -p ~/.hermes/workspace/治理/autonomy-memory-dryrun && cp ~/.hermes/memories/USER.md ~/.hermes/workspace/治理/autonomy-memory-dryrun/USER.preimage.$(date +%Y%m%d-%H%M%S).md", "apply_allowed": False},
                {"purpose": "size_readback", "command": "wc -c ~/.hermes/memories/USER.md ~/.hermes/memories/MEMORY.md ~/.hermes/SOUL.md", "apply_allowed": False},
                {"purpose": "post_verify", "command": "~/.hermes/bin/memory_runtime_health", "apply_allowed": False},
            ])
            patch_drafts.append({
                "target": str(HERMES_HOME / "memories" / "USER.md"),
                "type": "human_review_text_compaction",
                "instructions": [
                    "Do not delete stable preferences.",
                    "Merge duplicate autonomy/progress phrasing only.",
                    "Keep USER.md under health threshold, then run memory_runtime_health.",
                ],
                "apply_allowed": False,
            })
        elif action.get("id") == "triage_dirty_worktree":
            commands.extend([
                {"purpose": "dirty_status", "command": "git status --short", "apply_allowed": False},
                {"purpose": "dirty_diff_stat", "command": "git diff --stat", "apply_allowed": False},
                {"purpose": "scoped_tests", "command": "Run safe_checks listed in pgg_autonomy_observation_latest.json before any scoped commit.", "apply_allowed": False},
            ])
    return {
        "schema": "PGGAutonomyDryRunPacket/v0.8",
        "status": "DRY_RUN_READY" if commands or patch_drafts else "NO_DRY_RUN_NEEDED",
        "generated_at_epoch": status.generated_at_epoch,
        "triage_status": triage_packet.get("status"),
        "command_drafts": commands,
        "patch_drafts": patch_drafts,
        "artifact_paths": paths or {},
        "boundary": "dry-run packet only; reviewable commands/patch instructions, no execution, no file write, no commit, no revert, no provider/config/scheduler/security/production/legal mutation",
    }


def write_dry_run_packet(status: AutonomyStatus, triage_packet: dict[str, Any] | None = None, paths: dict[str, str] | None = None) -> dict[str, str]:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    packet = build_dry_run_packet(status, triage_packet, paths)
    latest_json = WORKSPACE / "pgg_autonomy_dryrun_latest.json"
    latest_md = WORKSPACE / "pgg_autonomy_dryrun_latest.md"
    ledger = WORKSPACE / "pgg_autonomy_dryrun_ledger.jsonl"
    latest_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_md.write_text("# PGG Autonomy Dry-run Packet\n\n```json\n" + json.dumps(packet, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(packet, ensure_ascii=False, sort_keys=True) + "\n")
    return {"dryrun_json": str(latest_json), "dryrun_md": str(latest_md), "dryrun_ledger": str(ledger)}


def compact_observation_payload(status: AutonomyStatus, paths: dict[str, str] | None = None, triage_packet: dict[str, Any] | None = None, dry_run_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return compact heartbeat/P0 alert payload for launchd logs."""
    summary = anomaly_summary(status)
    p0_items = [x for x in summary.get("items", []) if x.get("severity") == "P0"]
    triage_packet = triage_packet or build_p0_triage_packet(status, paths)
    dry_run_packet = dry_run_packet or build_dry_run_packet(status, triage_packet, paths)
    payload = {
        "schema": "PGGAutonomyCompactObservation/v0.8",
        "status": "ALERT_P0" if p0_items else "HEARTBEAT_OK",
        "generated_at_epoch": status.generated_at_epoch,
        "controller_schema": status.schema,
        "mode": status.mode,
        "anomaly_status": summary.get("status"),
        "severity_counts": summary.get("severity_counts", {}),
        "priority_counts": status.summary.get("priority_counts", {}),
        "next_item_id": (status.summary.get("next_item") or {}).get("id") if isinstance(status.summary.get("next_item"), dict) else None,
        "p0_items": p0_items[:10],
        "triage_status": triage_packet.get("status"),
        "triage_action_count": len(triage_packet.get("actions", [])),
        "dry_run_status": dry_run_packet.get("status"),
        "dry_run_command_count": len(dry_run_packet.get("command_drafts", [])),
        "dry_run_patch_count": len(dry_run_packet.get("patch_drafts", [])),
        "artifact_paths": paths or {},
        "boundary": "compact read-only heartbeat/alert with triage/dry-run summary; no fixes, no commits, no provider/config/scheduler/security/production/legal mutation",
    }
    return payload


def status_json(args: argparse.Namespace) -> dict[str, Any]:
    status = build_status(include_audit=not args.no_audit, mode=args.mode)
    paths = write_latest(status) if args.write_latest else {}
    return {**asdict(status), "artifacts": paths}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PGG Autonomy Controller")
    parser.add_argument("mode", choices=["status", "plan", "step", "observe"], nargs="?", default="status")
    parser.add_argument("--no-audit", action="store_true", help="skip npm audit probe for faster read-only status")
    parser.add_argument("--write-latest", action="store_true", help="write latest JSON/MD/ledger under workspace")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")
    parser.add_argument("--compact", action="store_true", help="for observe mode: print compact heartbeat/P0 alert JSON")
    args = parser.parse_args(argv)
    payload = status_json(args)
    if args.mode == "plan":
        payload["plan"] = [asdict(x) if not isinstance(x, dict) else x for x in build_status(include_audit=not args.no_audit, mode="plan").backlog]
    elif args.mode == "step":
        st = build_status(include_audit=not args.no_audit, mode="step")
        payload["step_proposal"] = asdict(st.backlog[0]) if st.backlog else None
        payload["execution_enabled"] = False
        payload["execution_boundary"] = "v0.4 classifies and proposes read-only safe checks only; no automatic mutation executor enabled"
    elif args.mode == "observe":
        st = build_status(include_audit=not args.no_audit, mode="observe")
        observation_paths = write_observation(st)
        triage_paths = write_triage_packet(st, observation_paths)
        triage_packet = build_p0_triage_packet(st, {**observation_paths, **triage_paths})
        dryrun_paths = write_dry_run_packet(st, triage_packet, {**observation_paths, **triage_paths})
        dry_run_packet = build_dry_run_packet(st, triage_packet, {**observation_paths, **triage_paths, **dryrun_paths})
        artifacts = {**payload.get("artifacts", {}), **observation_paths, **triage_paths, **dryrun_paths}
        payload = {**asdict(st), "anomaly_summary": anomaly_summary(st), "p0_triage_packet": triage_packet, "dry_run_packet": dry_run_packet, "artifacts": artifacts}
        payload["observation_boundary"] = "v0.8 read-only observation + P0 triage + dry-run packet; no launchd/scheduler mutation in this CLI"
        if args.compact:
            payload = compact_observation_payload(st, artifacts, triage_packet, dry_run_packet)
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
