"""PGG 基因自动验证器 — LLM驱动的基因候选→verified管道

真实执行：
1. 从 evolution_genes 取 top candidate（fitness最高+证据等级最高）
2. 用可用 LLM 审计工具验证每条基因的真实性
3. 决定：verified / needs_review / rejected
4. 写回 DB

边界：
- 本地 SQLite + LLM 审计工具（不修改 Hermes core/provider/scheduler/security）
- 不声称 AGI/T5/ASI
- 每次循环只验证最多 BATCH_SIZE 条，防止 token 爆炸
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BOUNDARY = "pgg_gene_verifier; local DB + LLM audit tools; no AGI/T5/ASI claim"

# DB
DEFAULT_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")

# 每次最多验证 10 条——token 消耗可控
BATCH_SIZE = 10

# 晋升阈值（LLM验证通过后还需要fitness≥此值才正式promote）
MIN_FITNESS_FOR_VERIFIED = 200

# 拒绝阈值（fitness低于此值且验证失败的直接标记rejected）
REJECT_FITNESS_THRESHOLD = 50


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _log(msg: str) -> None:
    print(f"[{_now()}] {msg}")


def _open_db(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def get_candidate_genes(con: sqlite3.Connection, limit: int = BATCH_SIZE) -> list[dict]:
    """获取最优候选基因：优先证据等级高+fitness高的未处理candidate"""
    cur = con.execute("""
        SELECT gene_id, gene_name, defect_name, fitness, evidence_grade,
               verification_status, absorbed_knowledge, source_refs_json,
               repair_mechanism
        FROM evolution_genes
        WHERE status='candidate'
          AND (verification_status IS NULL
               OR verification_status NOT LIKE '%LLM_VERIFIED%'
               OR verification_status NOT LIKE '%LLM_REJECTED%')
        ORDER BY
          CASE evidence_grade
            WHEN 'A' THEN 0 WHEN 'A-' THEN 1 WHEN 'B+' THEN 2
            WHEN 'B' THEN 3 ELSE 4
          END,
          fitness DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cur.fetchall()]


def call_llm_audit(gene: dict) -> dict:
    """用 MCP LLM audit 工具验证基因真实性。

    由于当前上下文不可直接调用 MCP，这里生成一个标准验证提示词，
    写到一个临时文件供外部调用或手动检查。
    """
    prompt = f"""请验证以下"进化基因"的真实性和实用性。

## 基因信息
- ID: {gene['gene_id']}
- 名称: {gene['gene_name']}
- 缺陷: {gene['defect_name']}
- fitness分: {gene['fitness']}
- 证据等级: {gene['evidence_grade']}
- 验证状态: {gene['verification_status']}
- 吸收知识摘要: {gene['absorbed_knowledge'][:300]}
- 修复机制: {gene['repair_mechanism'][:200]}

## 验证标准
1. 这个基因描述的能力是否真实存在于PGG Archon系统中？
2. 它是一个具体可执行的规则/代码/门禁，还是一个模糊概念？
3. 如果它被晋升为verified，是否会在真实系统中有实际价值？
4. 给出判断：VERIFIED / NEEDS_REVIEW / REJECTED

## 边界
- 这是内部进化基因库的自动验证
- 不涉及法律办案
- 判断基于基因内容而非外部知识
"""

    # 写prompt到文件，供LLM audit工具读取
    out_dir = Path("/Users/appleoppa/.hermes/data/gene-verification-pending")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{gene['gene_id']}.json"
    payload = {
        "gene_id": gene["gene_id"],
        "prompt": prompt,
        "created_at": _now(),
        "boundary": BOUNDARY
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return {
        "gene_id": gene["gene_id"],
        "status": "PENDING_LLM",
        "prompt_path": str(out_path),
        "message": f"提示词已写入 {out_path}，需通过LLM audit工具执行验证"
    }


def process_llm_results(con: sqlite3.Connection, results: list[dict]) -> dict:
    """处理LLM验证结果，写入DB。

    Args:
        results: [{"gene_id": "...", "judgment": "VERIFIED|NEEDS_REVIEW|REJECTED",
                    "reason": "...", "fitness_score": 123}]
    """
    promoted = 0
    rejected = 0
    needs_review = 0

    for r in results:
        gene_id = r["gene_id"]
        judgment = r.get("judgment", "NEEDS_REVIEW")
        reason = r.get("reason", "")
        fitness = r.get("fitness_score", 0)

        if judgment == "VERIFIED" and fitness >= MIN_FITNESS_FOR_VERIFIED:
            con.execute("""
                UPDATE evolution_genes
                SET status='verified',
                    verification_status=verification_status || ';LLM_VERIFIED',
                    fitness=MAX(fitness, ?)
                WHERE gene_id=? AND status='candidate'
            """, (fitness, gene_id))
            promoted += 1
        elif judgment == "REJECTED":
            new_status = "rejected" if fitness < REJECT_FITNESS_THRESHOLD else "candidate"
            con.execute("""
                UPDATE evolution_genes
                SET status=?,
                    verification_status=verification_status || ';LLM_REJECTED'
                WHERE gene_id=? AND status='candidate'
            """, (new_status, gene_id))
            if new_status == "rejected":
                rejected += 1
            else:
                needs_review += 1
        else:
            con.execute("""
                UPDATE evolution_genes
                SET verification_status=verification_status || ';LLM_NEEDS_REVIEW'
                WHERE gene_id=?
            """, (gene_id,))
            needs_review += 1

    con.commit()
    return {"promoted": promoted, "rejected": rejected, "needs_review": needs_review}


def run_verification_cycle(db_path: Path = DEFAULT_DB, dry_run: bool = False) -> dict:
    """运行一轮基因验证。

    1. 获取候选基因
    2. 生成LLM验证提示词
    3. 写pending目录等待LLM audit
    4. 报告结果
    """
    _log(f"=== 基因验证闭环开始 (dry_run={dry_run}) ===")
    con = _open_db(db_path)

    candidates = get_candidate_genes(con)
    _log(f"  查找到 {len(candidates)} 条待验证candidate基因")

    results = []
    for gene in candidates:
        result = call_llm_audit(gene)
        results.append(result)
        _log(f"  → {gene['gene_id']}: {result['status']}")

    if not dry_run:
        _log("  dry_run=True，未写入DB")
        con.close()
        return {
            "dry_run": True,
            "pending_count": len(results),
            "pending_dir": "/Users/appleoppa/.hermes/data/gene-verification-pending/",
            "message": "提示词已写入pending目录，下次系统会话中调用LLM audit工具处理"
        }

    # 真实模式：目前支持从 pending 目录读回LLM判断结果
    pending_dir = Path("/Users/appleoppa/.hermes/data/gene-verification-pending")
    verdicts = []
    for f in sorted(pending_dir.glob("*.verdict.json")):
        verdicts.append(json.loads(f.read_text()))
        f.unlink()  # 处理完删除

    if verdicts:
        stats = process_llm_results(con, verdicts)
        _log(f"  晋升: {stats['promoted']}, 拒绝: {stats['rejected']}, 需复查: {stats['needs_review']}")
    else:
        _log("  无LLM裁决结果待处理")

    # 报告
    total = con.execute("SELECT COUNT(*) FROM evolution_genes").fetchone()[0]
    by_status = dict(con.execute("SELECT status, COUNT(*) FROM evolution_genes GROUP BY status").fetchall())
    by_evidence = dict(con.execute("SELECT evidence_grade, COUNT(*) FROM evolution_genes WHERE evidence_grade IS NOT NULL GROUP BY evidence_grade ORDER BY COUNT(*) DESC LIMIT 5").fetchall())

    con.close()
    return {
        "dry_run": dry_run,
        "total": total,
        "by_status": by_status,
        "by_evidence": by_evidence,
        "processed": len(verdicts),
        "boundary": BOUNDARY
    }


def process_pending_verdicts(db_path: Path = DEFAULT_DB) -> dict:
    """处理所有等待中的LLM裁决。"""
    _log("=== 处理待处理LLM裁决 ===")
    con = _open_db(db_path)
    pending_dir = Path("/Users/appleoppa/.hermes/data/gene-verification-pending")

    verdicts = []
    for f in sorted(pending_dir.glob("*.verdict.json")):
        verdicts.append(json.loads(f.read_text()))

    if not verdicts:
        _log("  无待处理裁决")
        con.close()
        return {"processed": 0}

    stats = process_llm_results(con, verdicts)
    for f in sorted(pending_dir.glob("*.verdict.json")):
        f.unlink()

    con.close()
    _log(f"  处理 {stats}")
    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="dry_run模式（默认），不写DB")
    parser.add_argument("--real", action="store_true",
                        help="真实模式，写DB + 处理pending裁决")
    parser.add_argument("--process", action="store_true",
                        help="仅处理待处理LLM裁决")
    args = parser.parse_args()

    if args.process:
        result = process_pending_verdicts()
    else:
        run_real = args.real
        result = run_verification_cycle(dry_run=not run_real)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))