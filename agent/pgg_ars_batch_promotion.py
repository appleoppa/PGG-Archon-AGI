"""ARS batch gated promotion.

Small-batch candidate -> proof-review -> transaction loop for PGG GeneDB.
Boundaries:
- backs up GeneDB before any transaction batch
- only candidate genes with fitness >= threshold are considered
- proof_review_gene() must return approve and no mutation
- by default promotion requires dual_agreed or DeepSeek arbitration channel
- no credentials/config/scheduler/security changes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.pgg_bridge_processor import DB_PATH, _promote_gene, bridge_processor_summary, gene_db_write_lock, proof_review_gene

EVIDENCE_ROOT = Path("/Users/appleoppa/.hermes/workspace/pgg-archon-governance")
DEFAULT_TASK_PREFIX = "ars_batch_gated_promotion"
DEFAULT_LIMIT = 3
PROMOTABLE_CHANNELS = {"dual_agreed", "deepseek", "dual_fallback_highest_conf"}
STRICT_PROMOTABLE_CHANNELS = {"dual_agreed", "deepseek"}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_db(task_id: str) -> dict[str, Any]:
    backup_path = DB_PATH.with_suffix(DB_PATH.suffix + f".before-{task_id}.bak")
    shutil.copy2(DB_PATH, backup_path)
    return {
        "source": str(DB_PATH),
        "backup": str(backup_path),
        "sha256": _sha256(backup_path),
        "size": backup_path.stat().st_size,
    }


def candidate_rows(limit: int = DEFAULT_LIMIT, min_fitness: int = 700, gene_ids: list[str] | None = None) -> list[dict[str, Any]]:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    if gene_ids:
        placeholders = ",".join("?" for _ in gene_ids)
        rows = db.execute(
            f"""SELECT gene_id, gene_name, fitness, evidence_grade, verification_status, created_at
                FROM evolution_genes
                WHERE status='candidate' AND coalesce(fitness,0) >= ? AND gene_id IN ({placeholders})
                ORDER BY fitness DESC, created_at DESC
                LIMIT ?""",
            (min_fitness, *gene_ids, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT gene_id, gene_name, fitness, evidence_grade, verification_status, created_at
                FROM evolution_genes
                WHERE status='candidate' AND coalesce(fitness,0) >= ?
                ORDER BY fitness DESC, created_at DESC
                LIMIT ?""",
            (min_fitness, limit),
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def _read_status(gene_id: str) -> dict[str, Any]:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    row = db.execute(
        "SELECT gene_id,status,verification_status,evidence_grade,fitness,last_executed FROM evolution_genes WHERE gene_id=?",
        (gene_id,),
    ).fetchone()
    db.close()
    return dict(row) if row else {"gene_id": gene_id, "missing": True}


def decision_channel(review: dict[str, Any]) -> str:
    return str(review.get("decision", {}).get("channel", ""))


def is_promotable_review(review: dict[str, Any], strict_dual: bool = True) -> tuple[bool, str]:
    if review.get("verdict") != "PASS_DUAL_REVIEW_NO_MUTATION":
        return False, f"verdict_not_pass:{review.get('verdict')}"
    if review.get("mutation_detected") or review.get("external_concurrent_mutation"):
        return False, "external_concurrent_mutation"
    decision = review.get("decision", {})
    if decision.get("decision") != "approve":
        return False, f"decision_not_approve:{decision.get('decision')}"
    channel = str(decision.get("channel", ""))
    allowed = STRICT_PROMOTABLE_CHANNELS if strict_dual else PROMOTABLE_CHANNELS
    if channel not in allowed:
        return False, f"channel_not_promotable:{channel}"
    return True, "promotable"


def run_batch(limit: int = DEFAULT_LIMIT, min_fitness: int = 700, task_id: str | None = None,
              gene_ids: list[str] | None = None, strict_dual: bool = True,
              dry_run: bool = False) -> dict[str, Any]:
    task_id = task_id or f"{DEFAULT_TASK_PREFIX}_{_utc_stamp()}"
    evidence_dir = EVIDENCE_ROOT / task_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    before_summary = bridge_processor_summary()
    candidates = candidate_rows(limit=limit, min_fitness=min_fitness, gene_ids=gene_ids)
    db_backup = None if dry_run or not candidates else backup_db(task_id)

    result: dict[str, Any] = {
        "schema": "pgg_ars_batch_gated_promotion/v1",
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "limit": limit,
        "min_fitness": min_fitness,
        "strict_dual": strict_dual,
        "candidate_count": len(candidates),
        "before_summary": before_summary,
        "db_backup": db_backup,
        "items": [],
        "promoted": 0,
        "held": 0,
        "errors": 0,
        "lock": None,
    }

    with gene_db_write_lock(f"ars_batch:{task_id}") as lock_info:
        result["lock"] = lock_info
        for cand in candidates:
            gene_id = cand["gene_id"]
            item: dict[str, Any] = {"candidate": cand, "before": _read_status(gene_id)}
            if item["before"].get("status") != "candidate":
                item["proof_review"] = {"skipped": True, "reason": "not_candidate_at_locked_start"}
                item["promotion_precheck"] = {"ok": False, "reason": "not_candidate_at_locked_start", "channel": ""}
                item["transaction"] = {"skipped": True, "reason": "not_candidate_at_locked_start"}
                item["after"] = _read_status(gene_id)
                result["held"] += 1
                result["items"].append(item)
                continue
            review = proof_review_gene(gene_id, task_id=task_id)
            item["proof_review"] = review
            ok, reason = is_promotable_review(review, strict_dual=strict_dual)
            item["promotion_precheck"] = {"ok": ok, "reason": reason, "channel": decision_channel(review)}
            review_path = evidence_dir / f"proof_review_{gene_id}.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2))
            item["proof_review_path"] = str(review_path)

            if ok and not dry_run:
                tx = _promote_gene(gene_id, cand.get("evidence_grade") or "B", int(review.get("decision", {}).get("confidence") or 0), "dual_reviewed_batch_gated")
                item["transaction"] = tx
                item["after"] = _read_status(gene_id)
                if tx.get("promoted") and tx.get("affected", 0) == 1 and item["after"].get("status") == "verified":
                    result["promoted"] += 1
                else:
                    result["errors"] += 1
            else:
                item["transaction"] = {"skipped": True, "reason": reason if not dry_run else "dry_run"}
                item["after"] = _read_status(gene_id)
                result["held"] += 1
            result["items"].append(item)

    result["after_summary"] = bridge_processor_summary()
    result["remaining_ge700_candidates"] = len(candidate_rows(limit=10_000, min_fitness=min_fitness))
    result["verdict"] = (
        "PASS_ARS_BATCH_GATED_PROMOTION" if result["promoted"] > 0 and result["errors"] == 0
        else "WATCH_ARS_BATCH_NO_PROMOTION" if result["promoted"] == 0 and result["errors"] == 0
        else "WATCH_ARS_BATCH_ERRORS"
    )
    result_path = evidence_dir / "ARS_BATCH_GATED_PROMOTION_RESULT.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    result["result_path"] = str(result_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="PGG ARS batch gated promotion")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--min-fitness", type=int, default=700)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--gene-id", action="append", default=[])
    parser.add_argument("--allow-fallback", action="store_true", help="allow dual_fallback_highest_conf channel")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    res = run_batch(
        limit=args.limit,
        min_fitness=args.min_fitness,
        task_id=args.task_id or None,
        gene_ids=args.gene_id or None,
        strict_dual=not args.allow_fallback,
        dry_run=args.dry_run,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
