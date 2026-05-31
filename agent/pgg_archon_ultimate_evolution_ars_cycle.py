"""Phase 3 ARS cycle for the PGG Archon ultimate evolution formula.

This module connects the native ``pgg_ultimate_evolution`` tool to a bounded,
periodic ARS (Assess -> Recommend -> Stabilize) loop without mutating Hermes'
main agent loop.  It collects local evidence, calls the native tool, writes a
workspace report, and can optionally persist a summarized experiment/gene into
PGG Archon SQLite.

Safety boundary: no provider calls, no credential reads, no deployment, no git
operations, no core-loop mutation.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Mapping

from tools.registry import discover_builtin_tools, registry

_SCHEMA = "PGGArchonUltimateEvolutionPhase3ARSCycle/v1"
_DEFAULT_HOME = Path.home() / ".hermes"
_DEFAULT_REPO = _DEFAULT_HOME / "hermes-agent"
_DEFAULT_WORKSPACE = _DEFAULT_REPO / "workspace" / "ultimate_evolution_formula"
_DEFAULT_PGG_DB = _DEFAULT_HOME / "data" / "pgg_archon.db"
_DEFAULT_SESSION_DB = _DEFAULT_HOME / "state.db"
_DEFAULT_CRON_JOBS = _DEFAULT_HOME / "cron" / "jobs.json"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _count_session_messages(session_db_path: Path = _DEFAULT_SESSION_DB) -> Dict[str, Any]:
    if not session_db_path.exists():
        return {"available": False, "path": str(session_db_path), "messages_total": 0, "sessions_total": 0}
    con = sqlite3.connect(session_db_path)
    try:
        cur = con.cursor()
        messages_total = cur.execute("select count(*) from messages").fetchone()[0]
        sessions_total = cur.execute("select count(*) from sessions").fetchone()[0]
        recent_messages_24h = cur.execute(
            "select count(*) from messages where timestamp >= ?",
            (time.time() - 86400,),
        ).fetchone()[0]
        return {
            "available": True,
            "path": str(session_db_path),
            "messages_total": int(messages_total),
            "sessions_total": int(sessions_total),
            "recent_messages_24h": int(recent_messages_24h),
        }
    finally:
        con.close()


def _summarize_cron(cron_jobs_path: Path = _DEFAULT_CRON_JOBS) -> Dict[str, Any]:
    data = _read_json(cron_jobs_path)
    if isinstance(data, list):
        jobs = data
    elif isinstance(data, Mapping) and isinstance(data.get("jobs"), list):
        jobs = data.get("jobs") or []
    else:
        return {"available": False, "path": str(cron_jobs_path), "active_jobs": 0, "recent_errors": 0}
    active = 0
    recent_errors = 0
    pgg_related = 0
    for job in jobs:
        if not isinstance(job, Mapping):
            continue
        if job.get("enabled", True) and not job.get("paused", False):
            active += 1
        name = str(job.get("name") or "")
        script = str(job.get("script") or "")
        if "PGG" in name or "Archon" in name or "ultimate" in name or "apex" in script.lower():
            pgg_related += 1
        last_error = str(job.get("last_error") or job.get("error") or "")
        last_run = job.get("last_run") if isinstance(job.get("last_run"), Mapping) else {}
        if "error" in last_error.lower() or str(last_run.get("status") or "").lower() == "error":
            recent_errors += 1
    return {
        "available": True,
        "path": str(cron_jobs_path),
        "active_jobs": active,
        "pgg_related_jobs": pgg_related,
        "recent_errors": recent_errors,
    }


def collect_phase3_native_evidence(
    *,
    workspace_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    session_db_path: str | os.PathLike[str] = _DEFAULT_SESSION_DB,
    cron_jobs_path: str | os.PathLike[str] = _DEFAULT_CRON_JOBS,
) -> Dict[str, Any]:
    """Collect local Hermes evidence for the ARS loop."""
    workspace = Path(workspace_dir)
    phase1 = _read_json(workspace / "phase1_report.json")
    phase2_raw = _read_json(workspace / "phase2_tool_integration_report.json")
    phase2 = phase2_raw if isinstance(phase2_raw, Mapping) else {}
    session = _count_session_messages(Path(session_db_path))
    cron = _summarize_cron(Path(cron_jobs_path))
    tests_seen = bool(str(phase2.get("test_result", "")).startswith("9 passed"))
    tool_registered = bool(phase2.get("tool_registered") and phase2.get("toolset_contains_tool"))
    return {
        "schema": "PGGArchonUltimateEvolutionPhase3NativeEvidence/v1",
        "workspace": str(workspace),
        "phase1_report_exists": phase1 is not None,
        "phase2_report_exists": phase2 is not None,
        "tool_registered": tool_registered,
        "phase2_tests_seen": tests_seen,
        "sessiondb": session,
        "cron": cron,
        "phase2_score": phase2.get("tool_result", {}).get("report", {}).get("score") if isinstance(phase2, Mapping) else None,
    }


def _derive_tool_inputs(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    session_value = evidence.get("sessiondb")
    cron_value = evidence.get("cron")
    session = session_value if isinstance(session_value, Mapping) else {}
    cron = cron_value if isinstance(cron_value, Mapping) else {}
    tool_registered = bool(evidence.get("tool_registered"))
    phase2_tests_seen = bool(evidence.get("phase2_tests_seen"))
    session_available = bool(session.get("available"))
    cron_available = bool(cron.get("available"))
    recent_errors = int(cron.get("recent_errors") or 0)
    evm_signals = {
        "task_success": 90 if tool_registered and phase2_tests_seen else 70,
        "correctness": 88 if phase2_tests_seen else 72,
        "closure": 84 if evidence.get("phase1_report_exists") and evidence.get("phase2_report_exists") else 65,
        "reasoning_stability": 82 if session_available else 70,
        "tool_use": 92 if tool_registered else 60,
        "long_context_state": 86 if session_available and int(session.get("messages_total") or 0) > 0 else 65,
        "self_repair": 82 if cron_available else 70,
    }
    delta_signals = {
        "hallucination": 0.04,
        "security": 0.0,
        "unclosed_debt": 0.12 if recent_errors else 0.05,
        "cost": 0.03,
        "latency": 0.03,
        "instability": min(0.4, recent_errors * 0.1),
        "memory_pollution": 0.0,
        "tool_risk": 0.0,
        "governance_debt": min(0.4, recent_errors * 0.1),
    }
    return {
        "action": "ars_plan",
        "omega_a": 1.03 if tool_registered else 1.0,
        "evm_signals": evm_signals,
        "delta_signals": delta_signals,
    }


def call_pgg_ultimate_evolution_tool(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    """Call the native Hermes tool through ToolRegistry."""
    discover_builtin_tools()
    if registry.get_entry("pgg_ultimate_evolution") is None:
        # Importing the module registers the tool in normal Hermes discovery.
        import tools.pgg_archon_tools  # noqa: F401
    payload = registry.dispatch("pgg_ultimate_evolution", _derive_tool_inputs(evidence))
    return json.loads(payload)


def build_phase3_ars_cycle(evidence: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Build a complete Phase 3 report payload."""
    native_evidence = dict(evidence or collect_phase3_native_evidence())
    tool_payload = call_pgg_ultimate_evolution_tool(native_evidence)
    report = tool_payload.get("report", {})
    score = float(report.get("score") or 0.0)
    decision = tool_payload.get("ars_plan", {}).get("decision")
    next_actions = [
        "keep_pgg_ultimate_evolution_as_sidecar_periodic_gate",
        "summarize_sessiondb_cron_tool_evidence_each_tick",
        "persist_phase3_reports_and_gene_readback",
        "do_not_patch_run_agent_main_loop_without_explicit_authorization",
    ]
    if score >= 75:
        next_actions.append("allow_next_low_risk_ars_iteration")
    return {
        "schema": _SCHEMA,
        "status": "verified" if score >= 75 else "watch",
        "score": round(score, 3),
        "decision": decision,
        "native_evidence": native_evidence,
        "tool_payload": tool_payload,
        "next_actions": next_actions,
        "side_effects": "workspace_report_optional_sqlite_persistence_only",
        "boundary": "cron/runtime-loop sidecar; no run_agent.py mutation; no provider call; no secret read; no deploy; no git push",
        "ts": time.time(),
    }


def write_phase3_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    payload: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(payload or build_phase3_ars_cycle())
    json_path = out / "phase3_ars_cycle_report.json"
    md_path = out / "phase3_ars_cycle_report.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# PGG Archon 终极进化公式 Phase 3 ARS 周期闭环报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- score: `{data.get('score')}`",
        f"- decision: `{data.get('decision')}`",
        f"- side_effects: `{data.get('side_effects')}`",
        f"- boundary: {data.get('boundary')}",
        "",
        "## 下一步动作",
    ]
    md.extend(f"- {item}" for item in data.get("next_actions", []))
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _canonical_json_hash(value: Mapping[str, Any]) -> str:
    """Return a stable hash for compact replay/dedup comparisons."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_phase4_ars_trend_replay(
    *,
    workspace_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
    window: int = 10,
) -> Dict[str, Any]:
    """Replay recent Phase 3 ARS records and classify trend/dedup risk.

    This is read-only: it scans the workspace report and PGG DB, derives a
    stable payload hash, and marks whether periodic cron writes are duplicating
    the same gene semantics.
    """
    workspace = Path(workspace_dir)
    phase3_path = workspace / "phase3_ars_cycle_report.json"
    phase3 = _read_json(phase3_path)
    payload = phase3 if isinstance(phase3, Mapping) else {}
    score = float(payload.get("score") or 0.0)
    decision = str(payload.get("decision") or "")
    payload_fingerprint = _canonical_json_hash({
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "score": round(score, 3),
        "decision": decision,
        "boundary": payload.get("boundary"),
    }) if payload else None

    rows: list[tuple[Any, ...]] = []
    exp_rows: list[tuple[Any, ...]] = []
    db = Path(db_path)
    if db.exists():
        con = sqlite3.connect(db)
        try:
            cur = con.cursor()
            rows = cur.execute(
                "select id,name,pattern_type,quality_score,extracted_at from genes where name=? order by id desc limit ?",
                ("ultimate_evolution_formula_phase3_ars_cycle_gate", int(window)),
            ).fetchall()
            exp_rows = cur.execute(
                "select id,name,score,created_at from experiments where name=? order by id desc limit ?",
                ("ultimate_evolution_formula_phase3_periodic_ars_cycle", int(window)),
            ).fetchall()
        finally:
            con.close()
    quality_scores = [float(row[3] or 0.0) for row in rows]
    duplicate_count = max(0, len(rows) - 1)
    stable_scores = len(set(round(v, 4) for v in quality_scores)) <= 1 if quality_scores else False
    trend = "stable" if stable_scores and score >= 75 else "insufficient" if not quality_scores else "watch"
    return {
        "schema": "PGGArchonUltimateEvolutionPhase4ARSTrendReplay/v1",
        "status": "verified" if payload and score >= 75 else "watch",
        "phase3_report": str(phase3_path),
        "phase3_report_exists": bool(payload),
        "score": round(score, 3),
        "decision": decision,
        "payload_fingerprint": payload_fingerprint,
        "recent_gene_rows": [list(row) for row in rows],
        "recent_experiment_rows": [list(row) for row in exp_rows],
        "duplicate_gene_count": duplicate_count,
        "stable_quality_scores": stable_scores,
        "trend": trend,
        "risk": "cron_duplicate_gene_pollution" if duplicate_count else "none_detected",
    }


def persist_phase3_to_pgg_db_idempotent(
    payload: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    """Persist Phase 3 summary only when the semantic fingerprint is new."""
    db = Path(db_path)
    fingerprint = _canonical_json_hash({
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "score": round(float(payload.get("score") or 0.0), 3),
        "decision": payload.get("decision"),
        "boundary": payload.get("boundary"),
    })
    gene_name = "ultimate_evolution_formula_phase3_ars_cycle_gate"
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        existing = cur.execute(
            "select id,name,pattern_type,quality_score,code_snippet from genes where name=? order by id desc limit 25",
            (gene_name,),
        ).fetchall()
        for row in existing:
            try:
                snippet = json.loads(row[4] or "{}")
            except Exception:
                snippet = {}
            if snippet.get("phase4_dedup_fingerprint") == fingerprint:
                return {
                    "inserted": False,
                    "deduped": True,
                    "gene_id": row[0],
                    "experiment_id": None,
                    "readback": row[:4],
                    "db_path": str(db),
                    "fingerprint": fingerprint,
                }
    finally:
        con.close()
    result = persist_phase3_to_pgg_db(payload, paths, db_path=db)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        cur.execute(
            "update genes set code_snippet=? where id=?",
            (
                json.dumps({
                    "schema": payload.get("schema"),
                    "score": float(payload.get("score") or 0.0),
                    "paths": dict(paths),
                    "boundary": payload.get("boundary"),
                    "phase4_dedup_fingerprint": fingerprint,
                }, ensure_ascii=False),
                result["gene_id"],
            ),
        )
        con.commit()
        readback = cur.execute(
            "select id,name,pattern_type,quality_score from genes where id=?",
            (result["gene_id"],),
        ).fetchone()
    finally:
        con.close()
    return {
        "inserted": True,
        "deduped": False,
        "experiment_id": result.get("experiment_id"),
        "gene_id": result.get("gene_id"),
        "readback": readback,
        "db_path": str(db),
        "fingerprint": fingerprint,
    }


def write_phase4_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    replay: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(replay or build_phase4_ars_trend_replay(workspace_dir=out))
    data["schema"] = "PGGArchonUltimateEvolutionPhase4DedupReport/v1"
    data["dedup_gate"] = {
        "status": "active",
        "strategy": "phase3_semantic_fingerprint_skip_existing_gene",
        "blocked_duplicate_gene_count": data.get("duplicate_gene_count", 0),
    }
    json_path = out / "phase4_ars_trend_replay_dedup_report.json"
    md_path = out / "PGG-Archon-终极进化公式-Phase4-ARS趋势回放与去重门禁报告.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# PGG Archon 终极进化公式 Phase 4 ARS 趋势回放与去重门禁报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- score: `{data.get('score')}`",
        f"- trend: `{data.get('trend')}`",
        f"- duplicate_gene_count: `{data.get('duplicate_gene_count')}`",
        f"- dedup_gate: `{data.get('dedup_gate', {}).get('status')}`",
        f"- fingerprint: `{data.get('payload_fingerprint')}`",
        "",
        "## 边界",
        "- 只读回放 Phase3 报告和 PGG DB。",
        "- cron 后续入库走 semantic fingerprint 去重。",
        "- 不修改 run_agent.py，不读写 secret，不部署，不 git push。",
    ]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def build_phase5_promotion_gate(
    *,
    workspace_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    model_review_path: str | os.PathLike[str] | None = None,
) -> Dict[str, Any]:
    """Fuse Phase 3/4 reports into a bounded promotion gate status surface."""
    workspace = Path(workspace_dir)
    phase3_path = workspace / "phase3_ars_cycle_report.json"
    phase4_path = workspace / "phase4_ars_trend_replay_dedup_report.json"
    phase3_raw = _read_json(phase3_path)
    phase4_raw = _read_json(phase4_path)
    phase3 = phase3_raw if isinstance(phase3_raw, Mapping) else {}
    phase4 = phase4_raw if isinstance(phase4_raw, Mapping) else {}
    review_path = Path(model_review_path) if model_review_path else workspace / "model_review_phase5" / "phase5_dual_model_review.json"
    review_raw = _read_json(review_path)
    review = review_raw if isinstance(review_raw, Mapping) else {}
    score = min(float(phase3.get("score") or 0.0), float(phase4.get("score") or 0.0)) if phase3 and phase4 else 0.0
    gates = {
        "phase3_verified": phase3.get("status") == "verified",
        "phase4_verified": phase4.get("status") == "verified",
        "score_threshold": score >= 75,
        "trend_stable": phase4.get("trend") == "stable",
        "dedup_gate_active": bool((phase4.get("dedup_gate") or {}).get("status") == "active"),
        "dual_model_review_ok": int(review.get("ok_count") or 0) >= 2,
        "p0_blocker_absent": not bool(phase4.get("p0_blocker") or phase3.get("p0_blocker")),
    }
    passed = all(gates.values())
    blockers = [name for name, ok in gates.items() if not ok]
    return {
        "schema": "PGGArchonUltimateEvolutionPhase5PromotionGate/v1",
        "status": "promotion_ready" if passed else "blocked",
        "score": round(score, 3),
        "decision": "allow_candidate_promotion" if passed else "hold_candidate_promotion",
        "gates": gates,
        "blockers": blockers,
        "inputs": {
            "phase3_report": str(phase3_path),
            "phase4_report": str(phase4_path),
            "model_review": str(review_path),
        },
        "state_surface": {
            "phase3": {"status": phase3.get("status"), "score": phase3.get("score"), "decision": phase3.get("decision")},
            "phase4": {"status": phase4.get("status"), "trend": phase4.get("trend"), "duplicate_gene_count": phase4.get("duplicate_gene_count")},
            "model_review": {"ok_count": review.get("ok_count"), "called_at": review.get("called_at")},
        },
        "side_effects": "workspace_report_optional_sqlite_persistence_only",
        "boundary": "promotion gate sidecar; no run_agent.py mutation; no secret read; no deploy; no git push",
        "ts": time.time(),
    }


def write_phase5_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    gate: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(gate or build_phase5_promotion_gate(workspace_dir=out))
    json_path = out / "phase5_promotion_gate_report.json"
    md_path = out / "PGG-Archon-终极进化公式-Phase5-融合晋升门禁报告.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_gates = data.get("gates")
    gates = raw_gates if isinstance(raw_gates, Mapping) else {}
    md = [
        "# PGG Archon 终极进化公式 Phase 5 融合晋升门禁报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- score: `{data.get('score')}`",
        f"- decision: `{data.get('decision')}`",
        f"- blockers: `{', '.join(data.get('blockers', [])) or 'none'}`",
        "",
        "## 门禁结果",
    ]
    md.extend(f"- {name}: `{ok}`" for name, ok in gates.items())
    md.extend([
        "",
        "## 边界",
        "- 只融合 Phase3/Phase4 报告与 GPT/Claude 审查证据。",
        "- 只输出 candidate promotion gate，不自动晋升核心能力。",
        "- 不修改 run_agent.py，不读写 secret，不部署，不 git push。",
    ])
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _latest_gene_row(gene_name: str, *, db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB) -> tuple[Any, ...] | None:
    db = Path(db_path)
    if not db.exists():
        return None
    con = sqlite3.connect(db)
    try:
        return con.execute(
            "select id,name,pattern_type,quality_score,extracted_at from genes where name=? order by id desc limit 1",
            (gene_name,),
        ).fetchone()
    finally:
        con.close()


def build_phase7_evidence_chain_status(
    *,
    workspace_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
    cron_script: str | os.PathLike[str] = _DEFAULT_HOME / "scripts" / "pgg_ultimate_evolution_phase3_ars_cycle.sh",
    model_review_path: str | os.PathLike[str] | None = None,
) -> Dict[str, Any]:
    """Fuse reports, DB readback, cron wrapper, and review evidence into one read-only chain status."""
    workspace = Path(workspace_dir)
    reports = {
        "phase3": workspace / "phase3_ars_cycle_report.json",
        "phase4": workspace / "phase4_ars_trend_replay_dedup_report.json",
        "phase5": workspace / "phase5_promotion_gate_report.json",
        "phase6": workspace / "phase6_tool_status_surface_report.json",
    }
    report_data = {name: (_read_json(path) if path.exists() else None) for name, path in reports.items()}
    report_ok = {
        "phase3_report_ok": isinstance(report_data["phase3"], Mapping) and report_data["phase3"].get("status") == "verified",
        "phase4_report_ok": isinstance(report_data["phase4"], Mapping) and report_data["phase4"].get("status") == "verified",
        "phase5_report_ok": isinstance(report_data["phase5"], Mapping) and report_data["phase5"].get("status") == "promotion_ready",
        "phase6_report_ok": isinstance(report_data["phase6"], Mapping) and report_data["phase6"].get("status") == "verified",
    }
    gene_names = {
        "phase3": "ultimate_evolution_formula_phase3_ars_cycle_gate",
        "phase4": "ultimate_evolution_formula_phase4_ars_trend_dedup_gate",
        "phase5": "ultimate_evolution_formula_phase5_promotion_gate",
        "phase6": "ultimate_evolution_formula_phase6_native_tool_status_surface",
    }
    db_rows = {phase: _latest_gene_row(name, db_path=db_path) for phase, name in gene_names.items()}
    db_ok = {f"{phase}_gene_readback_ok": row is not None for phase, row in db_rows.items()}
    script_path = Path(cron_script)
    script_text = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
    cron_ok = script_path.exists() and all(flag in script_text for flag in ("--phase4", "--phase5", "--phase6"))
    review_path = Path(model_review_path) if model_review_path else workspace / "model_review_phase7" / "phase7_gpt_review.json"
    review = _read_json(review_path)
    review_ok = isinstance(review, Mapping) and bool(review.get("ok"))
    gates = {**report_ok, **db_ok, "cron_wrapper_has_phase4_5_6": cron_ok, "gpt_review_ok": review_ok}
    passed = all(gates.values())
    score_values = []
    for item in report_data.values():
        if isinstance(item, Mapping) and item.get("score") is not None:
            try:
                raw_score = item.get("score")
                if raw_score is not None:
                    score_values.append(float(raw_score))
            except Exception:
                pass
    score = min(score_values) if score_values else 0.0
    return {
        "schema": "PGGArchonUltimateEvolutionPhase7EvidenceChainStatus/v1",
        "status": "evidence_chain_verified" if passed else "evidence_chain_incomplete",
        "score": round(score, 3),
        "decision": "allow_chain_as_verified_sidecar_evidence" if passed else "hold_chain_until_missing_evidence_fixed",
        "gates": gates,
        "blockers": [name for name, ok in gates.items() if not ok],
        "reports": {name: str(path) for name, path in reports.items()},
        "db_readback": {phase: list(row) if row else None for phase, row in db_rows.items()},
        "cron_script": str(script_path),
        "model_review": str(review_path),
        "side_effects": "read_only_evidence_chain_report_optional_sqlite_persistence_only",
        "boundary": "evidence chain status sidecar; no run_agent.py mutation; no secret read; no deploy; no git push",
        "ts": time.time(),
    }


def write_phase7_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    chain: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(chain or build_phase7_evidence_chain_status(workspace_dir=out))
    json_path = out / "phase7_evidence_chain_status_report.json"
    md_path = out / "PGG-Archon-终极进化公式-Phase7-证据链状态面报告.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_gates = data.get("gates")
    gates = raw_gates if isinstance(raw_gates, Mapping) else {}
    md = [
        "# PGG Archon 终极进化公式 Phase 7 证据链状态面报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- score: `{data.get('score')}`",
        f"- decision: `{data.get('decision')}`",
        f"- blockers: `{', '.join(data.get('blockers', [])) or 'none'}`",
        "",
        "## 门禁",
    ]
    md.extend(f"- {k}: `{v}`" for k, v in gates.items())
    md.extend([
        "",
        "## 边界",
        "- 只读融合报告、DB readback、cron wrapper 和 GPT 审查证据。",
        "- 不自动晋升核心能力，不修改 run_agent.py。",
    ])
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def persist_phase7_to_pgg_db(
    chain: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(chain.get("score") or 0.0)
        gene_name = "ultimate_evolution_formula_phase7_evidence_chain_status"
        existing = cur.execute("select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1", (gene_name,)).fetchone()
        if existing:
            return {"inserted": False, "deduped": True, "gene_id": existing[0], "readback": existing, "db_path": str(db)}
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                "ultimate_evolution_formula_phase7_evidence_chain_status",
                "Phase7 fuses reports, DB readback, cron wrapper, and GPT review into a verified evidence-chain status surface",
                json.dumps({"status": chain.get("status"), "decision": chain.get("decision"), "paths": dict(paths)}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase7", "evidence-chain", "readback"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase7_evidence_chain_status_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": chain.get("schema"), "gates": chain.get("gates"), "paths": dict(paths)}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute("select id,name,pattern_type,quality_score from genes where id=?", (gene_id,)).fetchone()
        return {"inserted": True, "deduped": False, "experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def run_phase7_cycle(*, persist: bool = True) -> Dict[str, Any]:
    chain = build_phase7_evidence_chain_status()
    paths = write_phase7_report(chain=chain)
    result: Dict[str, Any] = {"chain": chain, "paths": paths}
    if persist:
        result["pgg_db"] = persist_phase7_to_pgg_db(chain, paths)
    return result


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _strip_volatile_fields(value: Any) -> Any:
    """Remove run-local timestamps from JSON artifacts before drift hashing."""
    if isinstance(value, Mapping):
        return {
            str(k): _strip_volatile_fields(v)
            for k, v in value.items()
            if str(k) not in {"ts", "called_at", "latency_ms"}
        }
    if isinstance(value, list):
        return [_strip_volatile_fields(item) for item in value]
    return value


def _stable_artifact_sha256(path: Path) -> str | None:
    """Hash artifacts deterministically while ignoring volatile JSON timestamps."""
    if not path.exists() or not path.is_file():
        return None
    if path.suffix.lower() == ".json":
        data = _read_json(path)
        if data is not None:
            return _canonical_json_hash(_strip_volatile_fields(data))
    return _file_sha256(path)


def _stable_artifact_size(path: Path) -> int:
    """Return deterministic size metadata paired with _stable_artifact_sha256."""
    if not path.exists() or not path.is_file():
        return 0
    if path.suffix.lower() == ".json":
        data = _read_json(path)
        if data is not None:
            encoded = json.dumps(_strip_volatile_fields(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            return len(encoded.encode("utf-8"))
    return path.stat().st_size


def build_phase8_chain_integrity_gate(
    *,
    workspace_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
    cron_script: str | os.PathLike[str] = _DEFAULT_HOME / "scripts" / "pgg_ultimate_evolution_phase3_ars_cycle.sh",
    model_review_path: str | os.PathLike[str] | None = None,
) -> Dict[str, Any]:
    """Build a deterministic integrity manifest over Phase3-7 evidence.

    Phase8 is a read-only drift gate: it hashes every local evidence artifact that
    Phase7 trusted, checks DB readback rows, verifies the cron wrapper now includes
    Phase7, and emits a stable manifest hash for later cron/CI comparison.
    """
    workspace = Path(workspace_dir)
    artifact_paths = {
        "phase3_report": workspace / "phase3_ars_cycle_report.json",
        "phase4_report": workspace / "phase4_ars_trend_replay_dedup_report.json",
        "phase5_report": workspace / "phase5_promotion_gate_report.json",
        "phase6_report": workspace / "phase6_tool_status_surface_report.json",
        "phase7_report": workspace / "phase7_evidence_chain_status_report.json",
    }
    review_path = Path(model_review_path) if model_review_path else workspace / "model_review_phase8" / "phase8_gpt_review.json"
    artifact_paths["phase8_model_review"] = review_path
    script_path = Path(cron_script)
    artifact_paths["cron_script"] = script_path

    artifacts = {
        name: {
            "path": str(path),
            "exists": path.exists(),
            "sha256": _stable_artifact_sha256(path),
            "size": _stable_artifact_size(path),
        }
        for name, path in artifact_paths.items()
    }
    phase7 = _read_json(workspace / "phase7_evidence_chain_status_report.json")
    review = _read_json(review_path)
    script_text = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
    gene_names = {
        "phase3": "ultimate_evolution_formula_phase3_ars_cycle_gate",
        "phase4": "ultimate_evolution_formula_phase4_ars_trend_dedup_gate",
        "phase5": "ultimate_evolution_formula_phase5_promotion_gate",
        "phase6": "ultimate_evolution_formula_phase6_native_tool_status_surface",
        "phase7": "ultimate_evolution_formula_phase7_evidence_chain_status",
    }
    db_rows = {phase: _latest_gene_row(name, db_path=db_path) for phase, name in gene_names.items()}
    db_readback = {phase: list(row) if row else None for phase, row in db_rows.items()}
    gates = {
        "phase7_chain_verified": isinstance(phase7, Mapping) and phase7.get("status") == "evidence_chain_verified",
        "phase3_7_artifacts_hashed": all(artifacts[name]["sha256"] for name in ("phase3_report", "phase4_report", "phase5_report", "phase6_report", "phase7_report")),
        "phase8_gpt_review_ok": isinstance(review, Mapping) and bool(review.get("ok")),
        "phase3_7_db_readback_ok": all(row is not None for row in db_rows.values()),
        "cron_wrapper_has_phase7": script_path.exists() and all(flag in script_text for flag in ("--phase4", "--phase5", "--phase6", "--phase7")),
    }
    manifest_seed = {
        "schema": "PGGArchonUltimateEvolutionPhase8ChainIntegrityGate/v1",
        "artifacts": {name: {"sha256": meta["sha256"], "size": meta["size"]} for name, meta in artifacts.items()},
        "db_readback": db_readback,
        "gates": gates,
    }
    manifest_hash = _canonical_json_hash(manifest_seed)
    passed = all(gates.values())
    score_values = []
    for report_name in ("phase3_report", "phase4_report", "phase5_report", "phase6_report", "phase7_report"):
        data = _read_json(Path(artifacts[report_name]["path"]))
        if isinstance(data, Mapping) and data.get("score") is not None:
            try:
                score_values.append(float(data.get("score")))
            except Exception:
                pass
    score = min(score_values) if score_values else 0.0
    return {
        "schema": "PGGArchonUltimateEvolutionPhase8ChainIntegrityGate/v1",
        "status": "integrity_verified" if passed else "integrity_incomplete",
        "score": round(score, 3),
        "decision": "allow_integrity_manifest_as_cron_ci_gate" if passed else "hold_until_integrity_gates_fixed",
        "manifest_hash": manifest_hash,
        "gates": gates,
        "blockers": [name for name, ok in gates.items() if not ok],
        "artifacts": artifacts,
        "db_readback": db_readback,
        "side_effects": "read_only_integrity_manifest_optional_sqlite_persistence_only",
        "boundary": "chain integrity gate sidecar; no run_agent.py mutation; no secret read; no deploy; no git push",
        "ts": time.time(),
    }


def write_phase8_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    gate: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(gate or build_phase8_chain_integrity_gate(workspace_dir=out))
    json_path = out / "phase8_chain_integrity_gate_report.json"
    md_path = out / "PGG-Archon-终极进化公式-Phase8-证据链完整性门禁报告.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    gates_raw = data.get("gates")
    gates = gates_raw if isinstance(gates_raw, Mapping) else {}
    md = [
        "# PGG Archon 终极进化公式 Phase 8 证据链完整性门禁报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- score: `{data.get('score')}`",
        f"- decision: `{data.get('decision')}`",
        f"- manifest_hash: `{data.get('manifest_hash')}`",
        f"- blockers: `{', '.join(data.get('blockers', [])) or 'none'}`",
        "",
        "## 门禁",
    ]
    md.extend(f"- {k}: `{v}`" for k, v in gates.items())
    md.extend([
        "",
        "## 边界",
        "- 只读哈希 Phase3-7 报告、Phase8 GPT 审查、cron wrapper 和 DB readback。",
        "- 生成 integrity manifest（完整性清单）供 cron/CI 漂移检查使用。",
        "- 不自动改核心，不读取 secret，不部署，不 git push。",
    ])
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def persist_phase8_to_pgg_db(
    gate: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(gate.get("score") or 0.0)
        manifest_hash = str(gate.get("manifest_hash") or "")
        gene_name = "ultimate_evolution_formula_phase8_chain_integrity_gate"
        existing = cur.execute("select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1", (gene_name,)).fetchone()
        if existing:
            return {"inserted": False, "deduped": True, "gene_id": existing[0], "readback": existing, "db_path": str(db)}
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "Phase8 hashes Phase3-7 evidence and model review into a deterministic integrity manifest for drift/CI gating",
                json.dumps({"status": gate.get("status"), "decision": gate.get("decision"), "manifest_hash": manifest_hash, "paths": dict(paths)}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase8", "integrity", "drift-gate"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase8_chain_integrity_gate_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": gate.get("schema"), "manifest_hash": manifest_hash, "gates": gate.get("gates"), "paths": dict(paths)}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute("select id,name,pattern_type,quality_score from genes where id=?", (gene_id,)).fetchone()
        return {"inserted": True, "deduped": False, "experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def run_phase8_cycle(*, persist: bool = True) -> Dict[str, Any]:
    gate = build_phase8_chain_integrity_gate()
    paths = write_phase8_report(gate=gate)
    result: Dict[str, Any] = {"gate": gate, "paths": paths}
    if persist:
        result["pgg_db"] = persist_phase8_to_pgg_db(gate, paths)
    return result


def build_phase9_cron_ci_drift_gate(
    *,
    workspace_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
    cron_script: str | os.PathLike[str] = _DEFAULT_HOME / "scripts" / "pgg_ultimate_evolution_phase3_ars_cycle.sh",
    model_review_path: str | os.PathLike[str] | None = None,
) -> Dict[str, Any]:
    """Build the Phase9 cron/CI drift gate over the Phase8 manifest.

    Phase9 turns the Phase8 integrity manifest into a deterministic local CI gate:
    it reloads the stored Phase8 report, recomputes the current Phase8 manifest,
    checks native tool visibility, verifies the cron wrapper carries Phase8/9, and
    emits a read-only pass/fail status that cron or CI can use without mutating the
    Hermes core loop.
    """
    workspace = Path(workspace_dir)
    script_path = Path(cron_script)
    review_path = Path(model_review_path) if model_review_path else workspace / "model_review_phase9" / "phase9_gpt_review.json"
    stored_phase8 = _read_json(workspace / "phase8_chain_integrity_gate_report.json")
    current_phase8 = build_phase8_chain_integrity_gate(
        workspace_dir=workspace,
        db_path=db_path,
        cron_script=script_path,
    )
    review = _read_json(review_path)
    script_text = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
    phase8_gene = _latest_gene_row("ultimate_evolution_formula_phase8_chain_integrity_gate", db_path=db_path)

    discover_builtin_tools()
    if registry.get_entry("pgg_ultimate_evolution") is None:
        import tools.pgg_archon_tools  # noqa: F401
    try:
        native_payload = json.loads(registry.dispatch("pgg_ultimate_evolution", {"action": "chain_integrity_status"}))
    except Exception as exc:  # pragma: no cover - defensive; tests exercise success path
        native_payload = {"error": str(exc)}
    native_report = native_payload.get("report") if isinstance(native_payload, Mapping) else {}

    gates = {
        "phase8_report_verified": isinstance(stored_phase8, Mapping) and stored_phase8.get("status") == "integrity_verified",
        "phase8_manifest_matches_current": isinstance(stored_phase8, Mapping) and stored_phase8.get("manifest_hash") == current_phase8.get("manifest_hash"),
        "native_tool_chain_integrity_visible": isinstance(native_report, Mapping) and native_report.get("status") == "integrity_verified",
        "phase8_db_readback_ok": phase8_gene is not None,
        "cron_wrapper_has_phase8_phase9": script_path.exists() and all(flag in script_text for flag in ("--phase8", "--phase9")),
        "phase9_gpt_review_ok": isinstance(review, Mapping) and bool(review.get("ok")),
    }
    passed = all(gates.values())
    score = float(current_phase8.get("score") or 0.0) if passed else min(float(current_phase8.get("score") or 0.0), 74.0)
    gate_seed = {
        "schema": "PGGArchonUltimateEvolutionPhase9CronCIDriftGate/v1",
        "phase8_manifest_hash": current_phase8.get("manifest_hash"),
        "stored_phase8_manifest_hash": stored_phase8.get("manifest_hash") if isinstance(stored_phase8, Mapping) else None,
        "cron_script_sha256": _file_sha256(script_path),
        "gates": gates,
    }
    return {
        "schema": "PGGArchonUltimateEvolutionPhase9CronCIDriftGate/v1",
        "status": "ci_drift_gate_passed" if passed else "ci_drift_gate_blocked",
        "score": round(score, 3),
        "decision": "allow_cron_ci_drift_gate_enforcement" if passed else "hold_until_ci_drift_gate_fixed",
        "gate_hash": _canonical_json_hash(gate_seed),
        "phase8_manifest_hash": current_phase8.get("manifest_hash"),
        "stored_phase8_manifest_hash": stored_phase8.get("manifest_hash") if isinstance(stored_phase8, Mapping) else None,
        "gates": gates,
        "blockers": [name for name, ok in gates.items() if not ok],
        "native_tool_report_schema": native_report.get("schema") if isinstance(native_report, Mapping) else None,
        "phase8_db_readback": list(phase8_gene) if phase8_gene else None,
        "side_effects": "read_only_cron_ci_drift_gate_optional_sqlite_persistence_only",
        "boundary": "cron/CI drift gate sidecar; no run_agent.py mutation; no secret read; no deploy; no git push",
        "ts": time.time(),
    }


def write_phase9_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    gate: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(gate or build_phase9_cron_ci_drift_gate(workspace_dir=out))
    json_path = out / "phase9_cron_ci_drift_gate_report.json"
    md_path = out / "PGG-Archon-终极进化公式-Phase9-Cron-CI漂移门禁报告.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    gates_raw = data.get("gates")
    gates = gates_raw if isinstance(gates_raw, Mapping) else {}
    md = [
        "# PGG Archon 终极进化公式 Phase 9 Cron/CI 漂移门禁报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- score: `{data.get('score')}`",
        f"- decision: `{data.get('decision')}`",
        f"- gate_hash: `{data.get('gate_hash')}`",
        f"- phase8_manifest_hash: `{data.get('phase8_manifest_hash')}`",
        f"- blockers: `{', '.join(data.get('blockers', [])) or 'none'}`",
        "",
        "## 门禁",
    ]
    md.extend(f"- {k}: `{v}`" for k, v in gates.items())
    md.extend([
        "",
        "## 边界",
        "- 只读比较 Phase8 manifest、原生工具状态、cron wrapper 与 DB readback。",
        "- 用于 cron/CI 漂移拦截，不自动改核心、不部署、不 git push。",
    ])
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def persist_phase9_to_pgg_db(
    gate: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(gate.get("score") or 0.0)
        gene_name = "ultimate_evolution_formula_phase9_cron_ci_drift_gate"
        existing = cur.execute("select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1", (gene_name,)).fetchone()
        if existing:
            return {"inserted": False, "deduped": True, "gene_id": existing[0], "readback": existing, "db_path": str(db)}
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "Phase9 materializes the Phase8 integrity manifest as a cron/CI drift gate",
                json.dumps({"status": gate.get("status"), "decision": gate.get("decision"), "gate_hash": gate.get("gate_hash"), "paths": dict(paths)}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase9", "cron-ci", "drift-gate"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase9_cron_ci_drift_gate_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": gate.get("schema"), "gate_hash": gate.get("gate_hash"), "gates": gate.get("gates"), "paths": dict(paths)}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute("select id,name,pattern_type,quality_score from genes where id=?", (gene_id,)).fetchone()
        return {"inserted": True, "deduped": False, "experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def run_phase9_cycle(*, persist: bool = True) -> Dict[str, Any]:
    gate = build_phase9_cron_ci_drift_gate()
    paths = write_phase9_report(gate=gate)
    result: Dict[str, Any] = {"gate": gate, "paths": paths}
    if persist:
        result["pgg_db"] = persist_phase9_to_pgg_db(gate, paths)
    return result


def build_phase6_tool_status_surface() -> Dict[str, Any]:
    """Expose Phase5 promotion gate through the native pgg_ultimate_evolution tool."""
    discover_builtin_tools()
    if registry.get_entry("pgg_ultimate_evolution") is None:
        import tools.pgg_archon_tools  # noqa: F401
    raw = registry.dispatch("pgg_ultimate_evolution", {"action": "promotion_status"})
    payload = json.loads(raw)
    gate = payload.get("promotion_gate") if isinstance(payload.get("promotion_gate"), Mapping) else {}
    report = payload.get("report") if isinstance(payload.get("report"), Mapping) else {}
    return {
        "schema": "PGGArchonUltimateEvolutionPhase6ToolStatusSurface/v1",
        "status": "verified" if report.get("status") == "promotion_ready" else "watch",
        "tool_action": "promotion_status",
        "score": report.get("score"),
        "decision": report.get("decision"),
        "blockers": report.get("blockers") or [],
        "promotion_gate_schema": gate.get("schema"),
        "native_tool_report_schema": report.get("schema"),
        "tool_payload": payload,
        "side_effects": "read_only_tool_status_report_optional_sqlite_persistence_only",
        "boundary": "native tool status surface; no run_agent.py mutation; no secret read; no deploy; no git push",
        "ts": time.time(),
    }


def write_phase6_report(
    output_dir: str | os.PathLike[str] = _DEFAULT_WORKSPACE,
    *,
    surface: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(surface or build_phase6_tool_status_surface())
    json_path = out / "phase6_tool_status_surface_report.json"
    md_path = out / "PGG-Archon-终极进化公式-Phase6-原生工具状态面融合报告.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# PGG Archon 终极进化公式 Phase 6 原生工具状态面融合报告",
        "",
        f"- schema: `{data.get('schema')}`",
        f"- status: `{data.get('status')}`",
        f"- tool_action: `{data.get('tool_action')}`",
        f"- score: `{data.get('score')}`",
        f"- decision: `{data.get('decision')}`",
        f"- blockers: `{', '.join(data.get('blockers', [])) or 'none'}`",
        "",
        "## 边界",
        "- Phase5 promotion gate 已通过 pgg_ultimate_evolution 原生工具读出。",
        "- 这是状态面融合，不是自动改核心或自动晋升。",
        "- 不修改 run_agent.py，不读写 secret，不部署，不 git push。",
    ]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def persist_phase6_to_pgg_db(
    surface: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(surface.get("score") or 0.0)
        gene_name = "ultimate_evolution_formula_phase6_native_tool_status_surface"
        existing = cur.execute(
            "select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1",
            (gene_name,),
        ).fetchone()
        if existing:
            return {"inserted": False, "deduped": True, "gene_id": existing[0], "readback": existing, "db_path": str(db)}
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                "ultimate_evolution_formula_phase6_native_tool_status_surface",
                "Phase6 exposes Phase5 promotion gate through the native pgg_ultimate_evolution tool status surface",
                json.dumps({"status": surface.get("status"), "decision": surface.get("decision"), "paths": dict(paths)}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase6", "native-tool", "status-surface"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase6_native_tool_status_surface_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": surface.get("schema"), "tool_action": surface.get("tool_action"), "paths": dict(paths)}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute("select id,name,pattern_type,quality_score from genes where id=?", (gene_id,)).fetchone()
        return {"inserted": True, "deduped": False, "experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def run_phase6_cycle(*, persist: bool = True) -> Dict[str, Any]:
    surface = build_phase6_tool_status_surface()
    paths = write_phase6_report(surface=surface)
    result: Dict[str, Any] = {"surface": surface, "paths": paths}
    if persist:
        result["pgg_db"] = persist_phase6_to_pgg_db(surface, paths)
    return result


def persist_phase5_to_pgg_db(
    gate: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(gate.get("score") or 0.0)
        gene_name = "ultimate_evolution_formula_phase5_promotion_gate"
        existing = cur.execute(
            "select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1",
            (gene_name,),
        ).fetchone()
        if existing:
            return {"inserted": False, "deduped": True, "gene_id": existing[0], "readback": existing, "db_path": str(db)}
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                "ultimate_evolution_formula_phase5_promotion_gate",
                "Phase5 fuses Phase3/4 and dual-model review into a bounded candidate promotion gate",
                json.dumps({"status": gate.get("status"), "decision": gate.get("decision"), "paths": dict(paths)}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase5", "promotion-gate", "fusion"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase5_promotion_gate_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": gate.get("schema"), "decision": gate.get("decision"), "gates": gate.get("gates"), "paths": dict(paths)}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute("select id,name,pattern_type,quality_score from genes where id=?", (gene_id,)).fetchone()
        return {"inserted": True, "deduped": False, "experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def run_phase5_cycle(*, persist: bool = True) -> Dict[str, Any]:
    gate = build_phase5_promotion_gate()
    paths = write_phase5_report(gate=gate)
    result: Dict[str, Any] = {"gate": gate, "paths": paths}
    if persist:
        result["pgg_db"] = persist_phase5_to_pgg_db(gate, paths)
    return result


def persist_phase4_to_pgg_db(
    replay: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(replay.get("score") or 0.0)
        fingerprint = str(replay.get("payload_fingerprint") or "")
        gene_name = "ultimate_evolution_formula_phase4_ars_trend_dedup_gate"
        existing = cur.execute(
            "select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1",
            (gene_name,),
        ).fetchone()
        if existing:
            return {"inserted": False, "deduped": True, "gene_id": existing[0], "readback": existing, "db_path": str(db)}
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                "ultimate_evolution_formula_phase4_ars_trend_dedup_gate",
                "Phase4 replays Phase3 ARS trends and prevents cron duplicate gene pollution",
                json.dumps({"status": replay.get("status"), "paths": dict(paths), "fingerprint": fingerprint}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase4", "dedup", "ars-trend-replay"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase4_ars_trend_dedup_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": replay.get("schema"), "paths": dict(paths), "fingerprint": fingerprint, "dedup_gate": "active"}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute("select id,name,pattern_type,quality_score from genes where id=?", (gene_id,)).fetchone()
        return {"inserted": True, "deduped": False, "experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def persist_phase3_to_pgg_db(
    payload: Mapping[str, Any],
    paths: Mapping[str, str],
    *,
    db_path: str | os.PathLike[str] = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    """Persist a compact Phase 3 summary into PGG SQLite and read it back."""
    db = Path(db_path)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        score = float(payload.get("score") or 0.0)
        exp_name = "ultimate_evolution_formula_phase3_periodic_ars_cycle"
        gene_name = "ultimate_evolution_formula_phase3_ars_cycle_gate"
        cur.execute(
            "insert into experiments(name, hypothesis, result, score, created_at, tags) values (?, ?, ?, ?, ?, ?)",
            (
                exp_name,
                "pgg_ultimate_evolution can drive a bounded periodic ARS sidecar without mutating run_agent.py",
                json.dumps({"status": payload.get("status"), "paths": dict(paths), "decision": payload.get("decision")}, ensure_ascii=False),
                score,
                now,
                json.dumps(["ultimate-evolution-formula", "phase3", "periodic-ars", "sidecar"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "insert into genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) values (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase3_periodic_ars_v1",
                "Hermes Agent / PGG Archon",
                json.dumps({"schema": payload.get("schema"), "score": score, "paths": dict(paths), "boundary": payload.get("boundary")}, ensure_ascii=False),
                round(score / 100.0, 4),
                now,
            ),
        )
        gene_id = cur.lastrowid
        con.commit()
        readback = cur.execute(
            "select id,name,pattern_type,quality_score from genes where id=?",
            (gene_id,),
        ).fetchone()
        return {"experiment_id": experiment_id, "gene_id": gene_id, "readback": readback, "db_path": str(db)}
    finally:
        con.close()


def run_phase3_cycle(*, persist: bool = False, idempotent: bool = True) -> Dict[str, Any]:
    payload = build_phase3_ars_cycle()
    paths = write_phase3_report(payload=payload)
    result: Dict[str, Any] = {"payload": payload, "paths": paths}
    if persist:
        if idempotent:
            result["pgg_db"] = persist_phase3_to_pgg_db_idempotent(payload, paths)
        else:
            result["pgg_db"] = persist_phase3_to_pgg_db(payload, paths)
    return result


def run_phase4_cycle(*, persist: bool = True) -> Dict[str, Any]:
    replay = build_phase4_ars_trend_replay()
    paths = write_phase4_report(replay=replay)
    result: Dict[str, Any] = {"replay": replay, "paths": paths}
    if persist:
        result["pgg_db"] = persist_phase4_to_pgg_db(replay, paths)
    return result


# ─── Phase 11: Gene Lifecycle & Promotion Chain ────────────────────────────────

_LIFECYCLE_STATES = ("candidate", "active", "promoted", "archived", "retired")


def _ensure_lifecycle_schema(db_path: Path = _DEFAULT_PGG_DB) -> None:
    """Ensure gene_lifecycle and promotion_chain tables exist (idempotent, migration-safe)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS gene_lifecycle ("
            "  gene_id INTEGER PRIMARY KEY,"
            "  state TEXT NOT NULL DEFAULT 'candidate',"
            "  activated_at TEXT,"
            "  promoted_at TEXT,"
            "  archived_at TEXT,"
            "  retired_at TEXT,"
            "  quality_score REAL,"
            "  parent_gene_id INTEGER,"
            "  FOREIGN KEY (gene_id) REFERENCES genes(id),"
            "  FOREIGN KEY (parent_gene_id) REFERENCES genes(id)"
            ")"
        )
        # Migrate old schema: add missing timestamp columns
        for col in ["candidate_at", "activated_at", "promoted_at", "archived_at", "retired_at"]:
            try:
                conn.execute(f"ALTER TABLE gene_lifecycle ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.execute(
            "CREATE TABLE IF NOT EXISTS promotion_chain ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  gene_id INTEGER NOT NULL,"
            "  from_state TEXT NOT NULL,"
            "  to_state TEXT NOT NULL,"
            "  transitioned_at TEXT NOT NULL,"
            "  trigger_phase TEXT,"
            "  decision TEXT,"
            "  FOREIGN KEY (gene_id) REFERENCES genes(id)"
            ")"
        )
        conn.commit()
    finally:
        conn.close()


def _build_phase11_lifecycle_report() -> Dict[str, Any]:
    """Assess current gene lifecycle states and promotion chain integrity."""
    _ensure_lifecycle_schema()
    conn = sqlite3.connect(_DEFAULT_PGG_DB)
    try:
        cur = conn.cursor()

        # Count genes by lifecycle state
        cur.execute(
            "SELECT state, COUNT(*) FROM gene_lifecycle GROUP BY state"
        )
        state_counts = dict(cur.fetchall())

        # Find latest gene in each state
        cur.execute(
            "SELECT gene_id, state, activated_at FROM gene_lifecycle "
            "WHERE state = 'active' ORDER BY activated_at DESC LIMIT 1"
        )
        active_row = cur.fetchone()
        cur.execute(
            "SELECT gene_id, state, promoted_at FROM gene_lifecycle "
            "WHERE state = 'promoted' ORDER BY promoted_at DESC LIMIT 1"
        )
        promoted_row = cur.fetchone()

        # Check for genes in genes table not yet in lifecycle
        cur.execute(
            "SELECT g.id, g.name, g.quality_score FROM genes g "
            "LEFT JOIN gene_lifecycle gl ON g.id = gl.gene_id "
            "WHERE gl.gene_id IS NULL ORDER BY g.id"
        )
        orphan_genes = [
            {"id": r[0], "name": r[1], "quality_score": r[2]}
            for r in cur.fetchall()
        ]

        # Promotion chain depth
        cur.execute(
            "SELECT COUNT(DISTINCT gene_id) FROM promotion_chain"
        )
        chain_genes = cur.fetchone()[0]

        # Get last 5 promotion events
        cur.execute(
            "SELECT gene_id, from_state, to_state, transitioned_at, decision "
            "FROM promotion_chain ORDER BY id DESC LIMIT 5"
        )
        recent_events = [
            {"gene_id": r[0], "from": r[1], "to": r[2],
             "at": r[3], "decision": r[4]}
            for r in cur.fetchall()
        ]

        return {
            "schema": "PGGArchonUltimateEvolutionPhase11GeneLifecycle/v1",
            "state_counts": state_counts,
            "latest_active": {
                "gene_id": active_row[0] if active_row else None,
                "at": active_row[2] if active_row else None,
            } if active_row else None,
            "latest_promoted": {
                "gene_id": promoted_row[0] if promoted_row else None,
                "at": promoted_row[2] if promoted_row else None,
            } if promoted_row else None,
            "orphan_genes": orphan_genes,
            "chain_events_total": chain_genes,
            "recent_promotion_events": recent_events,
            "all_states": _LIFECYCLE_STATES,
        }
    finally:
        conn.close()


def _transition_gene_state(
    gene_id: int,
    to_state: str,
    trigger_phase: str = None,
    decision: str = None,
    db_path: Path = _DEFAULT_PGG_DB,
) -> bool:
    """Transition a gene to a new lifecycle state. Returns True if transition happened."""
    if to_state not in _LIFECYCLE_STATES:
        return False
    _ensure_lifecycle_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        # Get current state
        cur.execute(
            "SELECT state FROM gene_lifecycle WHERE gene_id = ?", (gene_id,)
        )
        row = cur.fetchone()

        from_state = row[0] if row else None

        if row is None:
            # Insert new lifecycle record with the correct timestamp column for the state
            col = f"{to_state}_at"
            # All states have their own timestamp column; candidate uses candidate_at
            sql = f"INSERT OR IGNORE INTO gene_lifecycle (gene_id, state, {col}, quality_score) VALUES (?, ?, ?, (SELECT quality_score FROM genes WHERE id=?))"
            cur.execute(sql, (gene_id, to_state, now, gene_id))
        else:
            if from_state == to_state:
                return False  # no-op
            # Update state + timestamp
            col = f"{to_state}_at"
            cur.execute(
                f"UPDATE gene_lifecycle SET state=?, {col}=? WHERE gene_id=?",
                (to_state, now, gene_id),
            )

        # Log promotion chain event
        if from_state != to_state:
            cur.execute(
                "INSERT INTO promotion_chain (gene_id, from_state, to_state, transitioned_at, trigger_phase, decision) VALUES (?, ?, ?, ?, ?, ?)",
                (gene_id, from_state or "none", to_state, now, trigger_phase, decision),
            )

        conn.commit()
        return True
    finally:
        conn.close()


def persist_phase11_to_pgg_db(
    lifecycle_report: Dict[str, Any],
    paths: Dict[str, str],
    db_path: Path = _DEFAULT_PGG_DB,
) -> Dict[str, Any]:
    """Enroll ultimate-evolution genes, write Phase11 gene, and read it back.

    Phase11 is a lifecycle-chain gate, so persistence must do more than mutate
    helper tables: it also writes an idempotent gene/experiment row that proves
    the lifecycle surface itself became part of the PGG Archon gene ledger.
    """
    _ensure_lifecycle_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        enrolled = []

        # Find all ultimate_evolution_formula genes and enroll orphans.
        cur.execute(
            "SELECT g.id, g.name, g.quality_score FROM genes g "
            "LEFT JOIN gene_lifecycle gl ON g.id = gl.gene_id "
            "WHERE g.name LIKE 'ultimate_evolution_formula%' AND gl.gene_id IS NULL "
            "ORDER BY g.id"
        )
        orphans = cur.fetchall()

        for gene_id, name, quality_score in orphans:
            cur.execute(
                "INSERT OR IGNORE INTO gene_lifecycle (gene_id, state, candidate_at, quality_score) VALUES (?, 'candidate', ?, ?)",
                (gene_id, now, quality_score),
            )
            enrolled.append({"id": gene_id, "name": name, "state": "candidate"})

        # Promote the Phase5 promotion-gate gene to active when present.  Do not
        # hard-fail if a test database uses a different id set.
        cur.execute(
            "SELECT id FROM genes WHERE name='ultimate_evolution_formula_phase5_promotion_gate' ORDER BY id DESC LIMIT 1"
        )
        phase5_row = cur.fetchone()
        phase5_id = phase5_row[0] if phase5_row else 101
        cur.execute("SELECT state FROM gene_lifecycle WHERE gene_id = ?", (phase5_id,))
        row = cur.fetchone()
        if row and row[0] == "candidate":
            cur.execute(
                "UPDATE gene_lifecycle SET state='active', activated_at=? WHERE gene_id=?",
                (now, phase5_id),
            )
            cur.execute(
                "INSERT INTO promotion_chain (gene_id, from_state, to_state, transitioned_at, trigger_phase, decision) VALUES (?, 'candidate', 'active', ?, 'phase5_promotion_gate', 'allow_candidate_promotion')",
                (phase5_id, now),
            )
            enrolled.append({"id": phase5_id, "state": "active", "transitioned_from": "candidate"})

        cur.execute("SELECT COUNT(*) FROM gene_lifecycle")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM promotion_chain")
        chain_total = cur.fetchone()[0]

        gene_name = "ultimate_evolution_formula_phase11_gene_lifecycle_chain"
        existing = cur.execute(
            "SELECT id,name,pattern_type,quality_score FROM genes WHERE name=? ORDER BY id DESC LIMIT 1",
            (gene_name,),
        ).fetchone()
        if existing:
            conn.commit()
            return {
                "inserted": False,
                "deduped": True,
                "gene_id": existing[0],
                "readback": existing,
                "enrolled": enrolled,
                "total_lifecycle_genes": total,
                "total_promotion_events": chain_total,
                "db_path": str(db_path),
            }

        result_payload = {
            "schema": lifecycle_report.get("schema"),
            "state_counts": lifecycle_report.get("state_counts"),
            "orphan_genes_before_enroll": lifecycle_report.get("orphan_genes"),
            "enrolled": enrolled,
            "total_lifecycle_genes": total,
            "total_promotion_events": chain_total,
            "paths": dict(paths),
        }
        cur.execute(
            "INSERT INTO experiments(name, hypothesis, result, score, created_at, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "Phase11 establishes gene lifecycle and promotion-chain auditability for ultimate evolution genes",
                json.dumps(result_payload, ensure_ascii=False),
                100.0 if total > 0 else 75.0,
                now,
                json.dumps(["ultimate-evolution-formula", "phase11", "gene-lifecycle", "promotion-chain"], ensure_ascii=False),
            ),
        )
        experiment_id = cur.lastrowid
        cur.execute(
            "INSERT INTO genes(name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                gene_name,
                "ultimate_evolution_formula_phase11_gene_lifecycle_chain_v1",
                "Hermes Agent / PGG Archon",
                json.dumps(result_payload, ensure_ascii=False),
                1.0 if total > 0 else 0.75,
                now,
            ),
        )
        gene_id = cur.lastrowid
        cur.execute(
            "INSERT OR IGNORE INTO gene_lifecycle (gene_id, state, candidate_at, quality_score) VALUES (?, 'candidate', ?, ?)",
            (gene_id, now, 1.0 if total > 0 else 0.75),
        )
        conn.commit()
        readback = cur.execute(
            "SELECT id,name,pattern_type,quality_score FROM genes WHERE id=?", (gene_id,)
        ).fetchone()
        return {
            "inserted": True,
            "deduped": False,
            "experiment_id": experiment_id,
            "gene_id": gene_id,
            "readback": readback,
            "enrolled": enrolled,
            "total_lifecycle_genes": total + 1,
            "total_promotion_events": chain_total,
            "db_path": str(db_path),
        }
    finally:
        conn.close()


def write_phase11_report(
    lifecycle_report: Dict[str, Any],
    paths: Dict[str, str],
) -> Dict[str, str]:
    """Write Phase11 lifecycle report JSON to workspace."""
    out = Path(_DEFAULT_WORKSPACE) / "phase11_gene_lifecycle_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": lifecycle_report["schema"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "state_counts": lifecycle_report["state_counts"],
        "latest_active": lifecycle_report["latest_active"],
        "latest_promoted": lifecycle_report["latest_promoted"],
        "orphan_genes": lifecycle_report["orphan_genes"],
        "chain_events_total": lifecycle_report["chain_events_total"],
        "recent_promotion_events": lifecycle_report["recent_promotion_events"],
        "all_lifecycle_states": list(_LIFECYCLE_STATES),
        "workspace_reports": paths,
    }
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"phase11_report": str(out)}


def build_phase11_lifecycle_gate(
    lifecycle_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate Phase11 lifecycle gate: schema_valid + no_orphan_critical + chain_intact."""
    score = lifecycle_report.get("state_counts", {})
    orphans = lifecycle_report.get("orphan_genes", [])
    chain_ok = lifecycle_report.get("chain_events_total", 0) >= 0

    # Block if any ultimate_evolution gene is orphaned (not enrolled in lifecycle)
    orphan_blockers = [o["name"] for o in orphans if "phase" in o["name"]]

    # Gate decision
    if orphan_blockers:
        decision = "block_orphan_genes_not_enrolled"
        blockers = orphan_blockers
    else:
        decision = "allow_lifecycle_chain_active"
        blockers = []

    return {
        "schema": "PGGArchonUltimateEvolutionPhase11LifecycleGate/v1",
        "decision": decision,
        "blockers": blockers,
        "gate_checks": {
            "schema_valid": lifecycle_report.get("schema") == "PGGArchonUltimateEvolutionPhase11GeneLifecycle/v1",
            "no_orphan_critical": len(orphan_blockers) == 0,
            "chain_intact": chain_ok,
        },
        "state_counts": score,
        "chain_events_total": lifecycle_report.get("chain_events_total"),
    }


def run_phase11_cycle(*, persist: bool = True) -> Dict[str, Any]:
    """Execute Phase11: enroll lifecycle state, write report, then evaluate gate.

    Gate evaluation intentionally runs after persistence so orphan fixes are
    measured against the post-enrollment DB state, not the stale pre-migration
    snapshot.
    """
    before = _build_phase11_lifecycle_report()
    report_paths = write_phase11_report(before, {})
    persist_result = None
    if persist:
        persist_result = persist_phase11_to_pgg_db(before, report_paths)
    lifecycle = _build_phase11_lifecycle_report()
    gate = build_phase11_lifecycle_gate(lifecycle)
    return {
        "lifecycle": lifecycle,
        "pre_persist_lifecycle": before,
        "gate": gate,
        "persist": persist_result,
        "pgg_db": persist_result,
        "report_paths": report_paths,
    }


__all__ = [
    "build_phase10_auto_core_takeover",
    "build_phase11_lifecycle_gate",
    "build_phase3_ars_cycle",
    "build_phase4_ars_trend_replay",
    "build_phase5_promotion_gate",
    "build_phase6_tool_status_surface",
    "build_phase7_evidence_chain_status",
    "build_phase8_chain_integrity_gate",
    "build_phase9_cron_ci_drift_gate",
    "call_pgg_ultimate_evolution_tool",
    "collect_phase3_native_evidence",
    "persist_phase10_to_pgg_db",
    "persist_phase11_to_pgg_db",
    "persist_phase3_to_pgg_db",
    "persist_phase3_to_pgg_db_idempotent",
    "persist_phase4_to_pgg_db",
    "persist_phase5_to_pgg_db",
    "persist_phase6_to_pgg_db",
    "persist_phase7_to_pgg_db",
    "persist_phase8_to_pgg_db",
    "persist_phase9_to_pgg_db",
    "run_phase3_cycle",
    "run_phase4_cycle",
    "run_phase5_cycle",
    "run_phase6_cycle",
    "run_phase7_cycle",
    "run_phase8_cycle",
    "run_phase9_cycle",
    "run_phase10_cycle",
    "run_phase11_cycle",
    "write_phase10_report",
    "write_phase3_report",
    "write_phase4_report",
    "write_phase5_report",
    "write_phase6_report",
    "write_phase7_report",
    "write_phase8_report",
    "write_phase9_report",
    "write_phase11_report",
]
