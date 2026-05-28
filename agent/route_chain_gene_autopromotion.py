"""Controlled auto-write and promotion helpers for route-chain genes.

These helpers deliberately keep AGI evolution bounded: a candidate can be
written to the local gene DB only after the route-chain evidence hash checks,
real stage responses exist, GPT and Claude both participated, and an audit row
can be written. Promotion is an audited intent record, not a claim that AGI is
complete or that code was changed automatically.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

from agent.controlled_auto_core_patch import controlled_auto_core_patch

DEFAULT_GENE_DB_PATH = Path("/Users/appleoppa/.hermes/workspace/开智/02-进化基因/apex_evolution_genes.sqlite3")
DEFAULT_AUDIT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/auto-promotions")


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verify_embedded_hash(record: Mapping[str, Any], key: str) -> bool:
    copied = dict(record)
    embedded = copied.pop(key, None)
    return bool(embedded) and embedded == _sha256_obj(copied)


def validate_route_chain_gene_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if candidate.get("schema") != "route_chain_gene_candidate/v1":
        issues.append("schema_mismatch")
    if candidate.get("status") != "candidate_ready":
        issues.append("candidate_not_ready")
    if candidate.get("not_written_to_gene_db") is not True:
        issues.append("candidate_already_written_or_flag_missing")
    if not _verify_embedded_hash(candidate, "gene_hash"):
        issues.append("gene_hash_invalid")
    evidence_path = Path(str(candidate.get("source_evidence_path") or ""))
    if not evidence_path.exists():
        issues.append("source_evidence_missing")
        evidence = {}
    else:
        evidence = _load_json(evidence_path)
        if not _verify_embedded_hash(evidence, "record_hash"):
            issues.append("source_record_hash_invalid")
        if evidence.get("record_hash") != candidate.get("source_record_hash"):
            issues.append("source_hash_mismatch")
    raw_verification = candidate.get("verification")
    verification: Mapping[str, Any] = raw_verification if isinstance(raw_verification, Mapping) else {}
    if verification.get("record_hash_ok") is not True:
        issues.append("candidate_verification_record_hash_not_ok")
    if int(verification.get("stage_count") or 0) < 5:
        issues.append("stage_count_too_low")
    if int(verification.get("real_response_count") or 0) < int(verification.get("stage_count") or 0):
        issues.append("not_all_stages_real")
    if verification.get("gates"):
        issues.append("candidate_gates_not_empty")
    providers = set()
    if isinstance(evidence, Mapping):
        for stage in evidence.get("stage_outputs") or []:
            if isinstance(stage, Mapping) and stage.get("response_id"):
                providers.add(str(stage.get("provider") or ""))
    if candidate.get("task_class") == "evolution_agi":
        if "gpt55_5yuantoken" not in providers:
            issues.append("missing_gpt_stage")
        if "claude_opus47_5yuantoken" not in providers:
            issues.append("missing_claude_stage")
    status = "PASS" if not issues else "BLOCK"
    return {
        "schema": "RouteChainGeneCandidateValidation/v1",
        "status": status,
        "issues": issues,
        "candidate_id": candidate.get("gene_id"),
        "source_evidence_path": str(evidence_path) if evidence_path else "",
        "provider_count": len([p for p in providers if p]),
        "providers": sorted(p for p in providers if p),
        "agi_completion_claim": False,
    }


def _ensure_cycle(conn: sqlite3.Connection, cycle_id: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO evolution_cycles
        (cycle_id, created_at, theme, sequence_logic, status, evidence_grade, boundary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cycle_id,
            time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "量子路由+河图洛书自动候选基因受控入库",
            "14325：规划反证→证据门禁→候选固化→晋升审计",
            "active",
            "A-: route-chain evidence hash + real GPT/Claude stages",
            "受控入库，不代表AGI完成，不自动修改核心代码",
        ),
    )


def write_route_chain_candidate_to_gene_db(
    candidate_path: str | Path,
    *,
    db_path: str | Path = DEFAULT_GENE_DB_PATH,
) -> dict[str, Any]:
    candidate_path = Path(candidate_path)
    candidate = _load_json(candidate_path)
    validation = validate_route_chain_gene_candidate(candidate)
    if validation["status"] != "PASS":
        return {
            "schema": "RouteChainGeneAutoWrite/v1",
            "status": "BLOCK",
            "candidate_path": str(candidate_path),
            "validation": validation,
            "side_effects": "none",
            "agi_completion_claim": False,
        }
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    cycle_id = "ROUTE-CHAIN-AUTO-GENE-20260528"
    gene_id = str(candidate.get("gene_id"))
    row = {
        "cycle_id": cycle_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "defect_no": 1,
        "defect_name": "AGI/进化任务缺少强制多模型证据链",
        "gene_name": "量子路由+河图洛书五段链强制证据门禁基因",
        "absorbed_knowledge": str(candidate.get("candidate_rule") or "")[:1600],
        "source_refs_json": json.dumps([str(candidate_path), str(candidate.get("source_evidence_path"))], ensure_ascii=False),
        "repair_mechanism": "AGI/进化任务必须先经 route-chain evidence gate，GPT+Claude 真实参与并生成可校验 hash 后才允许候选入库。",
        "severity_rank": 1,
        "apex_variables": "Φ_anti,M_LCM,Ξ_repair,Ω_self_quality",
        "gate_type": "route_chain_hard_gate",
        "reusable_rule": "qr 只给候选排序；AGI/进化/核心改造必须经过 GPT+Claude 五段链证据门禁，不得单模型直通。",
        "status": "verified",
        "evidence_grade": "A-",
        "verification_status": "verified_by_route_chain_gate",
        "boundary": "自动写入仅记录受控基因；不声明AGI完成，不自动patch，不绕过人工/回滚门禁。",
        "gene_hash": str(candidate.get("gene_hash")),
    }
    conn = sqlite3.connect(db)
    try:
        _ensure_cycle(conn, cycle_id)
        conn.execute(
            """
            INSERT OR REPLACE INTO evolution_genes
            (gene_id, cycle_id, created_at, defect_no, defect_name, gene_name,
             absorbed_knowledge, source_refs_json, repair_mechanism, severity_rank,
             apex_variables, gate_type, reusable_rule, status, evidence_grade,
             verification_status, boundary, gene_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gene_id,
                row["cycle_id"],
                row["created_at"],
                row["defect_no"],
                row["defect_name"],
                row["gene_name"],
                row["absorbed_knowledge"],
                row["source_refs_json"],
                row["repair_mechanism"],
                row["severity_rank"],
                row["apex_variables"],
                row["gate_type"],
                row["reusable_rule"],
                row["status"],
                row["evidence_grade"],
                row["verification_status"],
                row["boundary"],
                row["gene_hash"],
            ),
        )
        conn.execute(
            "INSERT INTO verification_log(created_at, check_name, result, details) VALUES (?, ?, ?, ?)",
            (
                time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "route_chain_gene_auto_write",
                "pass",
                json.dumps({"gene_id": gene_id, "candidate_path": str(candidate_path), "validation": validation}, ensure_ascii=False, sort_keys=True),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    readback = sqlite3.connect(db)
    try:
        count = readback.execute("SELECT COUNT(*) FROM evolution_genes WHERE gene_id=?", (gene_id,)).fetchone()[0]
    finally:
        readback.close()
    return {
        "schema": "RouteChainGeneAutoWrite/v1",
        "status": "PASS" if count == 1 else "ERROR",
        "gene_id": gene_id,
        "candidate_path": str(candidate_path),
        "db_path": str(db),
        "validation": validation,
        "readback_count": count,
        "side_effects": "sqlite_gene_db_write_and_verification_log",
        "agi_completion_claim": False,
    }


def record_controlled_autonomous_promotion(
    gene_write_report: Mapping[str, Any],
    *,
    audit_dir: str | Path = DEFAULT_AUDIT_DIR,
    enable_core_patch: bool = False,
    core_patch_request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    audit_dir = Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)
    allowed = gene_write_report.get("status") == "PASS" and gene_write_report.get("validation", {}).get("status") == "PASS"
    record = {
        "schema": "RouteChainControlledAutonomousPromotion/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "PROMOTED_CONTROLLED" if allowed else "BLOCK",
        "gene_id": gene_write_report.get("gene_id"),
        "gene_write_status": gene_write_report.get("status"),
        "validation_status": gene_write_report.get("validation", {}).get("status") if isinstance(gene_write_report.get("validation"), Mapping) else None,
        "rollback_status": "pending",
        "rollback_plan": "disable route_chain_gate.hard_enforce / emit_gene_candidate / auto_write_gene_db and remove the inserted gene_id if validation is later disproved",
        "target": "route_chain_gene_db_and_runtime_gate_policy",
        "success": bool(allowed),
        "requires_human_review_for_core_patch": True,
        "agi_completion_claim": False,
    }
    record["promotion_hash"] = _sha256_obj(record)
    path = audit_dir / f"{int(time.time())}_{record.get('gene_id') or 'blocked'}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {**record, "audit_path": str(path)}
    if enable_core_patch:
        if not allowed:
            result["core_patch"] = {"status": "BLOCK", "issues": ["promotion_not_allowed"], "side_effects": "none"}
        elif not isinstance(core_patch_request, Mapping):
            result["core_patch"] = {"status": "BLOCK", "issues": ["core_patch_request_missing"], "side_effects": "none"}
        else:
            result["core_patch"] = controlled_auto_core_patch(
                promotion_path=str(path),
                target_path=str(core_patch_request.get("target_path") or ""),
                old_text=str(core_patch_request.get("old_text") or ""),
                new_text=str(core_patch_request.get("new_text") or ""),
                reason=str(core_patch_request.get("reason") or "route-chain controlled promotion callback"),
                verify_commands=core_patch_request.get("verify_commands") or [],
                allowlist=core_patch_request.get("allowlist") or (),
                audit_dir=core_patch_request.get("audit_dir") or Path("/Users/appleoppa/.hermes/workspace/agi-routing/core-patch-audits"),
                backup_dir=core_patch_request.get("backup_dir") or Path("/Users/appleoppa/.hermes/backups/auto_core_patch_runtime"),
                max_changed_chars=int(core_patch_request.get("max_changed_chars") or 12000),
            )
    return result


__all__ = [
    "validate_route_chain_gene_candidate",
    "write_route_chain_candidate_to_gene_db",
    "record_controlled_autonomous_promotion",
]
