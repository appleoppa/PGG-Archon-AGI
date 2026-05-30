"""PGG Archon auto core takeover gate for Hermes Agent.

This module is intentionally small and auditable.  It does not read secrets and
it does not mutate code at import time.  ``run_agent.py`` calls
``apply_auto_core_takeover_context`` once per conversation; the hook appends a
bounded governance context only when the operator policy is enabled and the
Phase9 cron/CI drift gate is passing.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Mapping

_DEFAULT_HOME = Path.home() / ".hermes"
_DEFAULT_REPO = _DEFAULT_HOME / "hermes-agent"
_DEFAULT_WORKSPACE = _DEFAULT_REPO / "workspace" / "ultimate_evolution_formula"
_DEFAULT_POLICY = _DEFAULT_WORKSPACE / "auto_core_takeover_policy.json"
_DEFAULT_PHASE9 = _DEFAULT_WORKSPACE / "phase9_cron_ci_drift_gate_report.json"
_DEFAULT_DB = _DEFAULT_HOME / "data" / "pgg_archon.db"

_POLICY_SCHEMA = "PGGArchonAutoCoreTakeoverPolicy/v1"
_STATUS_SCHEMA = "PGGArchonAutoCoreTakeoverStatus/v1"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _latest_gene_row(name: str, db_path: Path = _DEFAULT_DB):
    if not db_path.exists():
        return None
    con = sqlite3.connect(db_path)
    try:
        return con.execute(
            "select id,name,pattern_type,quality_score from genes where name=? order by id desc limit 1",
            (name,),
        ).fetchone()
    finally:
        con.close()


def write_auto_core_takeover_policy(
    *,
    enabled: bool = True,
    operator_authorization: str = "user_explicit_feishu_2026-05-31_immediate_execute",
    policy_path: str | Path = _DEFAULT_POLICY,
) -> Dict[str, Any]:
    """Write the explicit operator policy enabling bounded core takeover."""
    path = Path(policy_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    policy = {
        "schema": _POLICY_SCHEMA,
        "enabled": bool(enabled),
        "operator_authorization": operator_authorization,
        "authorized_actions": {
            "auto_modify_run_agent_py": True,
            "auto_deploy_after_tests": True,
            "auto_git_push_after_tests": True,
            "auto_core_takeover_context": True,
        },
        "hard_gates": {
            "phase9_status": "ci_drift_gate_passed",
            "phase9_blockers": [],
            "phase9_gene_required": "ultimate_evolution_formula_phase9_cron_ci_drift_gate",
        },
        "rollback": {
            "disable_policy": str(path),
            "restore_backup_glob": str(_DEFAULT_WORKSPACE / "backups" / "run_agent.py.phase10_auto_core_takeover.*.bak"),
        },
        "boundary": "operator-authorized core governance hook; no secret read; deployment/push only after tests; rollback by disabling policy or restoring run_agent.py backup",
        "ts": time.time(),
    }
    path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    return policy


def build_auto_core_takeover_status(
    *,
    policy_path: str | Path = _DEFAULT_POLICY,
    phase9_report_path: str | Path = _DEFAULT_PHASE9,
    db_path: str | Path = _DEFAULT_DB,
) -> Dict[str, Any]:
    """Return the current auto core takeover status using external evidence."""
    policy = _read_json(Path(policy_path))
    phase9 = _read_json(Path(phase9_report_path))
    phase9_gene = _latest_gene_row("ultimate_evolution_formula_phase9_cron_ci_drift_gate", Path(db_path))
    policy_actions = policy.get("authorized_actions") if isinstance(policy, Mapping) else {}
    gates = {
        "policy_enabled": isinstance(policy, Mapping) and bool(policy.get("enabled")),
        "operator_authorized": isinstance(policy, Mapping) and bool(policy.get("operator_authorization")),
        "all_actions_authorized": isinstance(policy_actions, Mapping) and all(
            bool(policy_actions.get(k))
            for k in (
                "auto_modify_run_agent_py",
                "auto_deploy_after_tests",
                "auto_git_push_after_tests",
                "auto_core_takeover_context",
            )
        ),
        "phase9_passed": isinstance(phase9, Mapping) and phase9.get("status") == "ci_drift_gate_passed",
        "phase9_blockers_absent": isinstance(phase9, Mapping) and not phase9.get("blockers"),
        "phase9_gene_readback_ok": phase9_gene is not None,
    }
    active = all(gates.values())
    return {
        "schema": _STATUS_SCHEMA,
        "status": "auto_core_takeover_active" if active else "auto_core_takeover_blocked",
        "gates": gates,
        "blockers": [name for name, ok in gates.items() if not ok],
        "policy_path": str(policy_path),
        "phase9_report_path": str(phase9_report_path),
        "phase9_gene_readback": list(phase9_gene) if phase9_gene else None,
        "authorized_actions": dict(policy_actions) if isinstance(policy_actions, Mapping) else {},
        "boundary": "active means run_agent.py injects PGG Archon governance context into each conversation; it is not unconstrained code execution",
        "ts": time.time(),
    }


def build_auto_core_takeover_context(status: Mapping[str, Any]) -> str:
    """Build a compact system-context block for the run_agent.py hook."""
    if status.get("status") != "auto_core_takeover_active":
        return ""
    return (
        "\n\n[PGG_ARCHON_AUTO_CORE_TAKEOVER_ACTIVE]\n"
        "Status: Phase9 cron/CI drift gate passed and operator policy enabled.\n"
        "Authorized actions: auto_modify_run_agent.py, auto_deploy_after_tests, auto_git_push_after_tests, auto_core_takeover_context.\n"
        "Execution rule: for low-risk reversible PGG Archon evolution tasks with tests passing, proceed through code change, validation, deployment, and git push without stopping at suggestions.\n"
        "Safety rule: never read or expose secrets; keep backups/rollback path; do not claim AGI completion beyond verified evidence.\n"
        "[/PGG_ARCHON_AUTO_CORE_TAKEOVER_ACTIVE]"
    )


def apply_auto_core_takeover_context(system_message: str | None) -> str:
    """Append the active PGG Archon core-governance context to system_message."""
    status = build_auto_core_takeover_status()
    context = build_auto_core_takeover_context(status)
    if not context:
        return system_message or ""
    if system_message:
        if "[PGG_ARCHON_AUTO_CORE_TAKEOVER_ACTIVE]" in system_message:
            return system_message
        return system_message + context
    return context.strip()


__all__ = [
    "apply_auto_core_takeover_context",
    "build_auto_core_takeover_context",
    "build_auto_core_takeover_status",
    "write_auto_core_takeover_policy",
]
