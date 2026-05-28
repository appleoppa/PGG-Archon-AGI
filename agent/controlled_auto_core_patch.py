"""Controlled automatic core patch gate for PGG Archon.

This module is the only allowed entry point for automatic core patching.  It is
intentionally narrow: a patch can be applied only when a route-chain promotion
record is already controlled-promoted, the target file is allow-listed, a backup
is created, the patch is bounded, and verification commands pass.

It does not claim AGI completion.  It writes an audit record for both PASS and
BLOCK outcomes.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/core-patch-audits")
DEFAULT_BACKUP_DIR = Path("/Users/appleoppa/.hermes/backups/auto_core_patch_runtime")
DEFAULT_ALLOWLIST = (
    "agent/route_chain_evidence_gate.py",
    "agent/route_chain_gene_autopromotion.py",
    "agent/conversation_loop.py",
    "tests/agent/test_route_chain_evidence_gate.py",
    "tests/agent/test_route_chain_gene_autopromotion.py",
    "tests/agent/test_route_chain_hard_integration.py",
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (REPO_ROOT / p).resolve()
    if REPO_ROOT not in resolved.parents and resolved != REPO_ROOT:
        if not os.environ.get("PGG_AUTO_CORE_PATCH_ALLOW_EXTERNAL_TEST_TARGETS"):
            raise ValueError("target_outside_repo")
    return resolved


def _rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _audit_path(audit_dir: str | Path, status: str, target: str) -> Path:
    safe = target.replace("/", "_").replace(".", "_")[:80]
    root = Path(audit_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{int(time.time())}_{status.lower()}_{safe}.json"


def validate_promotion_record(promotion_path: str | Path) -> dict[str, Any]:
    issues: list[str] = []
    p = Path(promotion_path)
    if not p.exists():
        return {"schema": "CorePatchPromotionValidation/v1", "status": "BLOCK", "issues": ["promotion_missing"]}
    data = _load_json(p)
    if data.get("schema") != "RouteChainControlledAutonomousPromotion/v1":
        issues.append("schema_mismatch")
    if data.get("status") != "PROMOTED_CONTROLLED" or data.get("success") is not True:
        issues.append("promotion_not_controlled_success")
    if data.get("agi_completion_claim") is not False:
        issues.append("agi_completion_claim_not_false")
    if not data.get("promotion_hash"):
        issues.append("promotion_hash_missing")
    if not data.get("rollback_plan"):
        issues.append("rollback_plan_missing")
    return {
        "schema": "CorePatchPromotionValidation/v1",
        "status": "PASS" if not issues else "BLOCK",
        "issues": issues,
        "gene_id": data.get("gene_id"),
        "promotion_path": str(p),
    }


def _run_checks(commands: Iterable[str], *, cwd: Path = REPO_ROOT, timeout: int = 180) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for cmd in commands:
        started = time.time()
        try:
            cp = subprocess.run(cmd, shell=True, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            output = (cp.stdout or "") + (cp.stderr or "")
            results.append({
                "command": cmd,
                "exit_code": cp.returncode,
                "output_hash": _sha256_text(output),
                "output_excerpt": output[-1200:],
                "latency_ms": int((time.time() - started) * 1000),
            })
        except Exception as exc:  # noqa: BLE001
            results.append({"command": cmd, "exit_code": 997, "error": type(exc).__name__, "latency_ms": int((time.time() - started) * 1000)})
    return results


def controlled_auto_core_patch(
    *,
    promotion_path: str | Path,
    target_path: str | Path,
    old_text: str,
    new_text: str,
    reason: str,
    verify_commands: Iterable[str],
    allowlist: Iterable[str] = DEFAULT_ALLOWLIST,
    audit_dir: str | Path = DEFAULT_AUDIT_DIR,
    backup_dir: str | Path = DEFAULT_BACKUP_DIR,
    max_changed_chars: int = 12000,
) -> dict[str, Any]:
    issues: list[str] = []
    promotion = validate_promotion_record(promotion_path)
    if promotion["status"] != "PASS":
        issues.extend(f"promotion:{x}" for x in promotion.get("issues", []))
    target = _repo_path(target_path)
    target_rel = _rel(target)
    allow = set(str(x) for x in allowlist)
    if target_rel not in allow:
        issues.append("target_not_allowlisted")
    if not target.exists():
        issues.append("target_missing")
    if not old_text:
        issues.append("old_text_empty")
    if old_text == new_text:
        issues.append("no_effect_patch")
    if abs(len(new_text) - len(old_text)) + len(new_text) > max_changed_chars:
        issues.append("patch_too_large")
    original = target.read_text(encoding="utf-8") if target.exists() else ""
    if old_text and original.count(old_text) != 1:
        issues.append("old_text_not_unique")
    before_hash = _sha256_text(original)
    audit_base = {
        "schema": "ControlledAutoCorePatchAudit/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "promotion": promotion,
        "target": target_rel,
        "reason": reason,
        "before_hash": before_hash,
        "agi_completion_claim": False,
        "side_effects": "none_until_gate_pass",
    }
    if issues:
        audit = {**audit_base, "status": "BLOCK", "issues": issues, "success": False}
        path = _audit_path(audit_dir, "BLOCK", target_rel)
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**audit, "audit_path": str(path)}

    backup_root = Path(backup_dir) / time.strftime("%Y%m%d_%H%M%S")
    backup_rel = target_rel.lstrip("/") if Path(target_rel).is_absolute() else target_rel
    backup_target = backup_root / backup_rel
    backup_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup_target)
    patched = original.replace(old_text, new_text, 1)
    target.write_text(patched, encoding="utf-8")
    after_hash = _sha256_file(target)
    diff = "".join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True), fromfile=f"a/{target_rel}", tofile=f"b/{target_rel}"))
    checks = _run_checks(verify_commands)
    checks_pass = all(item.get("exit_code") == 0 for item in checks)
    if not checks_pass:
        shutil.copy2(backup_target, target)
        restored_hash = _sha256_file(target)
        audit = {
            **audit_base,
            "status": "ROLLBACK",
            "success": False,
            "issues": ["verification_failed"],
            "after_hash": after_hash,
            "restored_hash": restored_hash,
            "backup_path": str(backup_target),
            "diff_hash": _sha256_text(diff),
            "verify_results": checks,
            "side_effects": "patched_then_rolled_back",
        }
        path = _audit_path(audit_dir, "ROLLBACK", target_rel)
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**audit, "audit_path": str(path)}
    audit = {
        **audit_base,
        "status": "PASS",
        "success": True,
        "issues": [],
        "after_hash": after_hash,
        "backup_path": str(backup_target),
        "diff_hash": _sha256_text(diff),
        "verify_results": checks,
        "side_effects": "target_file_patched_with_backup_and_verified",
    }
    path = _audit_path(audit_dir, "PASS", target_rel)
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**audit, "audit_path": str(path)}


__all__ = ["controlled_auto_core_patch", "validate_promotion_record"]
