#!/usr/bin/env python3
"""
PGG GeneDB 候选基因淘汰 (candidate→rejected) 管线。

纪律：
1. fitness < 70.0 且无 evidence_ref → 直接淘汰
2. fitness = 88.7 且无 evidence_ref 且无 parent_gene_id → bulk 冲量，标记 low_confidence
3. 只在 pgg_archon.db 主库操作
4. 只读保护：--dry-run 默认开启
"""

import sqlite3
import sys
from datetime import datetime, timezone

DB = str(__import__("pathlib").Path.home() / ".hermes/data/pgg_archon.db")


def prune(dry_run: bool = True) -> dict:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1) 低 fitness 淘汰池
    low_fit = cur.execute(
        "SELECT id, gene_id, ROUND(fitness_after,1) as f, evidence_ref, parent_gene_id "
        "FROM evolution_genes WHERE state='candidate' AND fitness_after < 70.0 "
        "AND (evidence_ref IS NULL OR evidence_ref = '')"
    ).fetchall()

    # 2) Bulk 冲量候选：fitness=88.7, 无 evidence, 无 parent
    bulk_low_confidence = cur.execute(
        "SELECT id, gene_id, created_at "
        "FROM evolution_genes WHERE state='candidate' AND fitness_after = 88.7 "
        "AND (evidence_ref IS NULL OR evidence_ref = '') "
        "AND parent_gene_id IS NULL"
    ).fetchall()

    result = {
        "low_fitness_reject": [],
        "bulk_low_confidence": [],
        "total_pruned": 0,
    }

    for row in low_fit:
        sql = "UPDATE evolution_genes SET state='rejected', retired_at=? WHERE id=?"
        now = datetime.now(timezone.utc).isoformat()
        if not dry_run:
            cur.execute(sql, (now, row["id"]))
        result["low_fitness_reject"].append({
            "id": row["id"], "gene_id": row["gene_id"], "fitness": row["f"],
        })

    for row in bulk_low_confidence:
        sql = "UPDATE evolution_genes SET state='rejected', retired_at=? WHERE id=?"
        now = datetime.now(timezone.utc).isoformat()
        if not dry_run:
            cur.execute(sql, (now, row["id"]))
        result["bulk_low_confidence"].append({
            "id": row["id"], "gene_id": row["gene_id"], "created_at": row["created_at"],
        })

    if not dry_run:
        conn.commit()

    conn.close()
    result["total_pruned"] = len(result["low_fitness_reject"]) + len(result["bulk_low_confidence"])
    result["dry_run"] = dry_run
    return result


if __name__ == "__main__":
    dry_run = "--no-dry-run" not in sys.argv
    r = prune(dry_run=dry_run)
    print(f"Dry-run={r['dry_run']}")
    print(f"低 fitness 淘汰: {len(r['low_fitness_reject'])}")
    print(f"Bulk 冲量淘汰: {len(r['bulk_low_confidence'])}")
    print(f"总淘汰: {r['total_pruned']}")
    if r['total_pruned'] == 0:
        print("无淘汰项，系统正常")
    else:
        print(f"\n低 fitness IDs: {[x['id'] for x in r['low_fitness_reject'][:10]]}{'...' if len(r['low_fitness_reject'])>10 else ''}")
        print(f"Bulk IDs: {[x['id'] for x in r['bulk_low_confidence'][:5]]}{'...' if len(r['bulk_low_confidence'])>5 else ''}")