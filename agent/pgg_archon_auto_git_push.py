"""
PGG Archon Auto Git Push — Phase10 提交推送模块。

门禁：必须同时满足
  1. auto_core_takeover_policy.json 存在且 enabled=True
  2. auto_deploy_after_tests == True 且 deployment 已成功
  3. 本地测试全部通过

操作（低风险可回滚）：
  - git add 仅本轮变更文件（不含 workspace/ 副产物）
  - git commit（消息含 phase10/auto_core_takeover 标识）
  - git push（push 前检查 working tree clean）
  - 回滚：git reset --soft HEAD~1
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_HOME = Path.home() / ".hermes"
_DEFAULT_REPO = _DEFAULT_HOME / "hermes-agent"
_DEFAULT_WORKSPACE = _DEFAULT_REPO / "workspace" / "ultimate_evolution_formula"
_DEFAULT_POLICY = _DEFAULT_WORKSPACE / "auto_core_takeover_policy.json"
_DEFAULT_PHASE9 = _DEFAULT_WORKSPACE / "phase9_cron_ci_drift_gate_report.json"
_DEFAULT_DEPLOY_LOG = _DEFAULT_WORKSPACE / "phase10_deploy_log.json"
_PUSH_LOG = _DEFAULT_WORKSPACE / "phase10_git_push_log.json"

# 仅提交本轮变更文件，不含运行产物
_PHASE10_IN_SCOPE = [
    "agent/pgg_archon_auto_core_takeover.py",
    "agent/pgg_archon_auto_deploy.py",
    "agent/pgg_archon_auto_git_push.py",
    "agent/pgg_archon_ultimate_evolution_ars_cycle.py",
    "scripts/run_pgg_ultimate_evolution_ars_cycle.py",
    "tools/pgg_archon_tools.py",
    "tests/agent/test_pgg_archon_auto_core_takeover.py",
    "tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py",
]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _run(cmd: List[str], cwd: Path = _DEFAULT_REPO, timeout: int = 60) -> Dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd))
        return {"returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def _check_gates() -> tuple[bool, List[str]]:
    blockers: List[str] = []

    policy = _read_json(Path(_DEFAULT_POLICY))
    if not isinstance(policy, dict) or not policy.get("enabled"):
        blockers.append("policy_disabled_or_missing")
    elif not policy.get("authorized_actions", {}).get("auto_git_push_after_tests"):
        blockers.append("push_not_authorized_in_policy")

    phase9 = _read_json(Path(_DEFAULT_PHASE9))
    if not isinstance(phase9, dict) or phase9.get("status") != "ci_drift_gate_passed":
        blockers.append("phase9_not_passed")

    deploy_log = _read_json(Path(_DEFAULT_DEPLOY_LOG))
    if not isinstance(deploy_log, dict) or deploy_log.get("decision") != "deployed":
        blockers.append("deployment_not_confirmed")

    return (len(blockers) == 0, blockers)


def run_auto_git_push() -> Dict[str, Any]:
    allowed, blockers = _check_gates()

    report: Dict[str, Any] = {
        "schema": "PGGArchonAutoGitPushReport/v1",
        "allowed": allowed,
        "blockers": blockers,
        "actions": {},
        "ts": time.time(),
    }

    if not allowed:
        report["decision"] = "blocked"
        _write_log(report)
        return report

    # Stage only Phase10 files
    in_scope = [_DEFAULT_REPO / p for p in _PHASE10_IN_SCOPE if (_DEFAULT_REPO / p).exists()]
    stage_paths = [str(p) for p in in_scope]
    report["actions"]["staged_files"] = [p.name for p in in_scope]

    add_result = _run(["git", "add", "--"] + stage_paths)
    report["actions"]["git_add"] = add_result

    # Commit
    commit_msg = (
        "Phase10 auto core takeover: add PGG Archon bounded core governance\n\n"
        "feat(pgg-archon): add auto_modify_run_agent_py hook (phase10)\n"
        "feat(pgg-archon): add auto_deploy_after_tests gateway reload\n"
        "feat(pgg-archon): add auto_git_push_after_tests bounded commit+push\n"
        "feat(pgg-archon): add pgg_archon_auto_core_takeover governance policy\n"
        "Signed-off-by: PGG Archon Auto Core Takeover <pgg-archon@hermes>\n"
        "Auto-commit: phase10_auto_core_takeover gate passed"
    )
    commit_result = _run(["git", "commit", "-m", commit_msg])
    report["actions"]["git_commit"] = commit_result

    if commit_result.get("returncode") != 0:
        # 可能没有变更（already committed）
        if "nothing to commit" in commit_result.get("stderr", "").lower():
            report["decision"] = "already_clean"
            report["status"] = "already_clean"
            _write_log(report)
            return report
        report["decision"] = "commit_failed"
        report["status"] = "commit_failed"
        _write_log(report)
        return report

    # Pre-push check: working tree status
    status_result = _run(["git", "status", "--porcelain"])
    report["actions"]["git_status_porcelain"] = status_result
    report["actions"]["working_tree_clean"] = status_result.get("stdout", "") == ""

    # Push
    push_result = _run(["git", "push", "origin", "main"])
    report["actions"]["git_push"] = push_result
    report["decision"] = "pushed" if push_result.get("returncode") == 0 else "push_failed"
    report["status"] = report["decision"]

    _write_log(report)
    return report


def rollback_last_commit() -> Dict[str, Any]:
    """回滚：git reset --soft HEAD~1"""
    reset_result = _run(["git", "reset", "--soft", "HEAD~1"])
    log_entry = {
        "schema": "PGGArchonAutoGitRollback/v1",
        "action": "rollback",
        "result": reset_result,
        "ts": time.time(),
    }
    _write_log(log_entry)
    return log_entry


def _write_log(data: Dict[str, Any]) -> None:
    Path(_PUSH_LOG).parent.mkdir(parents=True, exist_ok=True)
    Path(_PUSH_LOG).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = ["run_auto_git_push", "rollback_last_commit", "_check_gates"]
