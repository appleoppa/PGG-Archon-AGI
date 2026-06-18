"""PGG 自主演化闭环 — 全自动基因摄取/晋升/融合/报告。
直接操作真实 DB schema（gene_lifecycle + genes 表）。

三层管道：
1. promote — 将 quality_score 达标的 candidate 基因晋升为 promoted
2. fusion  — 对 top-N promoted/active 基因交叉融合，生成 offspring candidate
3. intake  — 从文件系统扫描代码模式，写入新 candidate

边界：
- 本地 SQLite + 文件系统，无网络/LLM 调用
- 可写 GeneDB（promote + fusion offspring 需要写入）
- 不修改 Hermes core/provider/scheduler/security
- 不声称 AGI/T5/ASI
"""

from __future__ import annotations

import json
import sqlite3
import hashlib
import sys
import time
import subprocess
from pathlib import Path
from typing import Any

BOUNDARY = "pgg_self_evolution_loop; local DB writes; no LLM/network; no AGI/T5/ASI claim"

# DB 路径 — pgg_archon.db 包含 gene_lifecycle + genes + evolution_genes 三表
DEFAULT_DB = Path('/Users/appleoppa/.hermes/data/pgg_archon.db')

# 晋升阈值（genes.quality_score 范围 20-58，用 35 作为较低门槛）
MIN_QUALITY_FOR_PROMOTION = 35
MAX_BATCH_PROMOTE = 50
FUSION_TOP_N = 20
MAX_FUSION_PAIRS = 30

LOOP_VERSION = "pgg_self_evolution_loop/v2"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _log(msg: str) -> None:
    print(f"[{_now()}] {msg}")


def _open_db(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


# ─── Phase 1: 晋升 candidate → promoted ───


def promote_candidates(db_path: Path = DEFAULT_DB, *, dry_run: bool = False) -> dict[str, Any]:
    from agent.pgg_bridge_processor import gene_db_write_lock
    with gene_db_write_lock("self_evolution_promote"):
        return _promote_candidates_unlocked(db_path, dry_run=dry_run)


def _promote_candidates_unlocked(db_path: Path = DEFAULT_DB, *, dry_run: bool = False) -> dict[str, Any]:
    """晋升 quality_score >= MIN_QUALITY_FOR_PROMOTION 的 candidate 基因 (gene_lifecycle)。"""
    con = _open_db(db_path)

    # 查 candidate 基因，关联 genes 表取 name/quality 信息
    candidates = con.execute(
        """
        SELECT gl.gene_id, gl.state, gl.quality_score AS lifecycle_quality,
               gl.candidate_at,
               g.name AS gene_name, g.pattern_type, g.source_repo,
               g.quality_score AS gene_quality
        FROM gene_lifecycle gl
        LEFT JOIN genes g ON gl.gene_id = g.id
        WHERE gl.state = 'candidate'
          AND COALESCE(gl.quality_score, g.quality_score) >= ?
        ORDER BY COALESCE(gl.quality_score, g.quality_score) DESC
        LIMIT ?
        """,
        (MIN_QUALITY_FOR_PROMOTION, MAX_BATCH_PROMOTE),
    ).fetchall()

    if not candidates:
        con.close()
        return {"schema": f"{LOOP_VERSION}/promote", "promoted": 0, "total_candidates": 0, "boundary": BOUNDARY}

    promoted = 0
    promoted_ids: list[str] = []
    skipped_reasons: dict[str, int] = {}

    for row in candidates:
        gid = row["gene_id"]
        q = float(row["lifecycle_quality"] or row["gene_quality"] or 0)

        # 防止重复晋升
        if gid in promoted_ids:
            skipped_reasons["duplicate"] = skipped_reasons.get("duplicate", 0) + 1
            continue

        if dry_run:
            promoted += 1
            promoted_ids.append(str(gid))
            continue

        # 写入 evolution_genes 表作为晋升记录
        now = _now()
        try:
            # 更新 gene_lifecycle state → 'promoted'
            con.execute(
                "UPDATE gene_lifecycle SET state = 'promoted', promoted_at = ? WHERE gene_id = ? AND state = 'candidate'",
                (now, gid),
            )
            # 插入 evolution_genes 追踪记录
            con.execute(
                """INSERT OR IGNORE INTO evolution_genes
                   (gene_id, parent_gene_id, state, generation, mutation_vector,
                    fitness_before, fitness_after, promoted_at, retired_at, evidence_ref, created_at)
                   VALUES (?, NULL, 'promoted', 1, 'auto_promoted', NULL, ?, ?, NULL, '{}', ?)""",
                (gid, q, now, now),
            )
            promoted += 1
            promoted_ids.append(str(gid))
        except sqlite3.OperationalError as e:
            skipped_reasons[f"db_error_{e}"] = skipped_reasons.get(f"db_error_{e}", 0) + 1

    con.commit()
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/promote",
        "created_at": _now(),
        "dry_run": dry_run,
        "promoted": promoted,
        "promoted_ids": promoted_ids[:20],
        "total_candidates": len(candidates),
        "skipped_reasons": skipped_reasons,
        "threshold": MIN_QUALITY_FOR_PROMOTION,
        "boundary": BOUNDARY,
    }


# ─── Phase 2: 融合 top promoted/active 基因 ───


def run_fusion_on_verified(db_path: Path = DEFAULT_DB, *, dry_run: bool = False) -> dict[str, Any]:
    """取 top-N promoted/active 基因，两两融合生成 offspring candidate。"""
    con = _open_db(db_path)

    parents = con.execute(
        """
        SELECT gl.gene_id, g.name, g.pattern_type, g.source_repo,
               COALESCE(
                 CASE WHEN gl.quality_score < 5.0 AND g.quality_score > 10.0 THEN g.quality_score
                      ELSE gl.quality_score
                 END,
                 g.quality_score, gl.quality_score
               ) AS quality_score
        FROM gene_lifecycle gl
        LEFT JOIN genes g ON gl.gene_id = g.id
        WHERE gl.state IN ('promoted', 'active')
        ORDER BY quality_score DESC
        LIMIT ?
        """,
        (FUSION_TOP_N,),
    ).fetchall()

    if len(parents) < 2:
        con.close()
        return {"schema": f"{LOOP_VERSION}/fusion", "fused": 0, "parents_count": len(parents),
                "reason": "not_enough_parents", "boundary": BOUNDARY}

    fused_count = 0
    fusion_results: list[dict[str, Any]] = []
    pairs_tried = 0

    for i in range(len(parents)):
        for j in range(i + 1, len(parents)):
            if pairs_tried >= MAX_FUSION_PAIRS:
                break

            p_a, p_b = parents[i], parents[j]
            pid_a, pid_b = int(p_a["gene_id"]), int(p_b["gene_id"])
            # 获取下一个可用 ID
            max_id = con.execute("SELECT COALESCE(MAX(id), 0) FROM genes").fetchone()[0]
            offspring_id = max_id + pairs_tried + 1
            avg_quality = (float(p_a["quality_score"] or 0) + float(p_b["quality_score"] or 0)) / 2

            fusion_results.append({
                "parents": [str(pid_a), str(pid_b)],
                "parents_name": [str(p_a["name"] or ""), str(p_b["name"] or "")],
                "avg_quality": round(avg_quality, 2),
            })

            if not dry_run:
                # 先写入 genes 表（FK 依赖）
                now = _now()
                try:
                    con.execute(
                        """INSERT OR IGNORE INTO genes
                           (id, name, pattern_type, source_repo, code_snippet, quality_score, extracted_at)
                           VALUES (?, ?, 'auto_fusion', 'self_evolution_loop', '', ?, ?)""",
                        (offspring_id, f"fusion_{p_a['name'] or ''}_{p_b['name'] or ''}"[:60].replace(' ','_'),
                         round(avg_quality, 2), now),
                    )
                    # 再写入 gene_lifecycle（FK → genes.id）
                    con.execute(
                        """INSERT OR IGNORE INTO gene_lifecycle
                           (gene_id, state, candidate_at, quality_score)
                           VALUES (?, 'candidate', ?, ?)""",
                        (offspring_id, now, round(avg_quality, 2)),
                    )
                    # 写入 evolution_genes 追踪
                    con.execute(
                        """INSERT OR IGNORE INTO evolution_genes
                           (gene_id, parent_gene_id, state, generation, mutation_vector,
                            fitness_before, fitness_after, created_at)
                           VALUES (?, ?, 'candidate', 1, 'auto_fusion', NULL, ?, ?)""",
                        (offspring_id, f"{pid_a},{pid_b}", round(avg_quality, 2), now),
                    )
                    fused_count += 1
                except sqlite3.IntegrityError:
                    pass  # 已存在

            pairs_tried += 1

    if not dry_run:
        con.commit()
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/fusion",
        "created_at": _now(),
        "dry_run": dry_run,
        "fused": fused_count,
        "total_pairs_attempted": pairs_tried,
        "verified_parents_count": len(parents),
        "sample_results": fusion_results[:5],
        "boundary": BOUNDARY,
    }


# ─── Phase 3: 代码扫描摄入新基因 ───

SCAN_DIRS = [
    "/Users/appleoppa/.hermes/hermes-agent/agent",
]


def _scan_for_patterns(root_dir: str) -> list[dict[str, Any]]:
    """扫描 Python 文件，检测 agent/tool/skill 模式，返回候选基因列表。"""
    candidates = []
    root = Path(root_dir)
    if not root.exists():
        return candidates

    for py_file in sorted(root.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # 检测模式
        if "def " in text and ("tool" in text.lower() or "agent" in text.lower()):
            # 提取函数数/行数
            func_count = text.count("def ")
            lines = text.count("\n") + 1
            if func_count >= 2 and lines >= 20:
                gene_id = hashlib.sha256(py_file.name.encode()).hexdigest()[:12]
                candidates.append({
                    "gene_id": gene_id,
                    "name": py_file.stem,
                    "pattern_type": "agent_module",
                    "source_repo": str(py_file),
                    "quality_score": min(func_count * 5 + lines * 0.1, 100),
                })
    return candidates


def run_intake_scan(write_candidates: bool = True, db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    """扫描 agent 目录，发现新基因模式并写入 candidate。"""
    con = _open_db(db_path)

    # 获取已有 gene_id 集合避免重复
    existing_ids = set()
    try:
        existing_ids = {str(r[0]) for r in con.execute("SELECT gene_id FROM genes").fetchall()}
    except Exception:
        pass

    scanned = 0
    written = 0

    for scan_dir in SCAN_DIRS:
        patterns = _scan_for_patterns(scan_dir)
        scanned += len(patterns)
        for pat in patterns:
            if pat["gene_id"] in existing_ids:
                continue
            if not write_candidates:
                continue

            now = _now()
            try:
                # 写入 genes 表
                con.execute(
                    """INSERT INTO genes (id, name, pattern_type, source_repo, code_snippet, quality_score, extracted_at)
                       VALUES (?, ?, ?, ?, '', ?, ?)""",
                    (pat["gene_id"], pat["name"], pat["pattern_type"],
                     pat["source_repo"], pat["quality_score"], now),
                )
                # 写入 gene_lifecycle
                con.execute(
                    """INSERT INTO gene_lifecycle
                       (gene_id, state, candidate_at, quality_score)
                       VALUES (?, 'candidate', ?, ?)""",
                    (pat["gene_id"], now, pat["quality_score"]),
                )
                written += 1
            except sqlite3.IntegrityError:
                pass

    if write_candidates and written > 0:
        con.commit()
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/intake",
        "created_at": _now(),
        "scanned_dirs": SCAN_DIRS,
        "candidates_found": scanned,
        "candidates_written": written,
        "boundary": BOUNDARY,
    }


# ─── Main 闭环 ───


def run_evolution_cycle(
    db_path: Path = DEFAULT_DB,
    *,
    dry_run: bool = False,
    skip_intake: bool = False,
) -> dict[str, Any]:
    """完整闭环：intake → promote → fusion → 聚合报告。"""
    _log("=== PGG 自主演化闭环开始 (dry_run=%s) ===" % dry_run)

    cycle = {
        "schema": f"{LOOP_VERSION}/cycle",
        "started_at": _now(),
        "dry_run": dry_run,
        "phases": {},
        "boundary": BOUNDARY,
    }

    # Phase 0: 自扫描知识缺口
    if not skip_intake:
        _log("Phase 0: 自扫描知识缺口 - 主动找学习方向...")
        intake_result = run_intake_scan(write_candidates=not dry_run, db_path=db_path)
        cycle["phases"]["intake"] = intake_result
        _log(f"  -> 扫描到 {intake_result['candidates_found']} 个候选, 写入 {intake_result['candidates_written']} 个")
    else:
        _log("Phase 0: 跳过 intake (skip_intake=True)")

    # Phase 1: 晋升
    _log("Phase 1: 晋升 candidate 基因...")
    promote_result = promote_candidates(db_path, dry_run=dry_run)
    cycle["phases"]["promote"] = promote_result
    _log(f"  -> 晋升了 {promote_result['promoted']} 个基因")

    # Phase 2: 融合
    _log("Phase 2: 融合 top verified 基因...")
    fusion_result = run_fusion_on_verified(db_path, dry_run=dry_run)
    cycle["phases"]["fusion"] = fusion_result
    _log(f"  -> 融合了 {fusion_result['fused']} 个 offspring")

    cycle["completed_at"] = _now()
    _log("=== PGG 自主演化闭环完成 ===")
    return cycle


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PGG 自主演化闭环")
    parser.add_argument("--dry-run", action="store_true", help="只模拟不写入")
    parser.add_argument("--no-intake", action="store_true", help="跳过 intake 阶段")
    args = parser.parse_args()

    result = run_evolution_cycle(dry_run=args.dry_run, skip_intake=args.no_intake)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()