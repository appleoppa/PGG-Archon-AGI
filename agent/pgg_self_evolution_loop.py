"""PGG 自主演化闭环 — 全自动基因摄取/晋升/融合/报告。
不再需要任何人插手。

三层管道：
1. promote — 将符合条件的 candidate 基因自动晋升为 verified
2. fusion  — 对 top-N verified 基因进行交叉融合，生成 offspring
3. intake  — 运行基因摄入循环（扫描代码 → 写 candidate）

边界：
- 本地 SQLite + 文件系统，无网络/LLM 调用
- 可写 GeneDB（promote + fusion offspring 需要写入）
- 不修改 Hermes core/provider/scheduler/security
- 不声称 AGI/T5/ASI
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import agent.pgg_archon_gene_fusion_engine as fusion
import agent.pgg_archon_standard_gene_backfill as backfill
import agent.pgg_aris_reflection as aris
import agent.pgg_dream_mode as dream
import agent.pgg_picoapex_saturation as picoapex
import agent.pgg_health_monitor as health

BOUNDARY = "pgg_self_evolution_loop; local DB writes; no LLM/network; no AGI/T5/ASI claim"

# DB
DEFAULT_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")

# 晋升阈值
MIN_FITNESS_FOR_PROMOTION = 700
MAX_BATCH_PROMOTE = 1000
MAX_FUSION_PARENTS = 50
FUSION_TOP_N = 20

# 循环版本
LOOP_VERSION = "pgg_self_evolution_loop/v1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _log(msg: str) -> None:
    ts = _now()
    print(f"[{ts}] {msg}")


def _open_db(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


# ─── Phase 1: 晋升（backfill + existing candidates） ───


def promote_candidates(db_path: Path = DEFAULT_DB, *, dry_run: bool = False) -> dict[str, Any]:
    """批量晋升所有符合条件的 candidate 基因。

    条件：
    - status='candidate'
    - 有 absorbed_knowledge（标准模板 JSON），含 signals_match
    - 有 evidence_grade
    - 有 source_refs_json（非空）
    - fitness >= MIN_FITNESS_FOR_PROMOTION
    """
    con = _open_db(db_path)
    candidates = con.execute(
        """
        SELECT gene_id, status, verification_status, fitness, evidence_grade,
               source_refs_json, absorbed_knowledge, gene_name, gate_type,
               severity_rank, boundary
        FROM evolution_genes
        WHERE status = 'candidate'
          AND absorbed_knowledge IS NOT NULL
          AND absorbed_knowledge LIKE '%signals_match%'
          AND evidence_grade IS NOT NULL AND evidence_grade != ''
          AND source_refs_json IS NOT NULL AND length(source_refs_json) > 10
          AND (fitness IS NOT NULL AND fitness >= ?)
        ORDER BY fitness DESC
        LIMIT ?
        """,
        (MIN_FITNESS_FOR_PROMOTION, MAX_BATCH_PROMOTE),
    ).fetchall()

    if not candidates:
        con.close()
        return {"schema": f"{LOOP_VERSION}/promote", "promoted": 0, "total_candidates": 0, "boundary": BOUNDARY}

    promoted = 0
    skipped_reasons: dict[str, int] = {}
    promoted_ids: list[str] = []

    for row in candidates:
        gid = row["gene_id"]

        # 跳过已经是 verified_by_* 的
        vstat = str(row["verification_status"] or "")
        if vstat.startswith("verified"):
            skipped_reasons["already_verified"] = skipped_reasons.get("already_verified", 0) + 1
            continue

        # ═══════════════════════════════════════════════════════════
        # 永久基因膨胀门禁：绝对不自动晋升未经验证的回填/待审查基因
        # 2026-06-12: 发现 88 条 STANDARD_ 被误升 → 增加此门禁
        # ═══════════════════════════════════════════════════════════
        BLOCKED_PREFIXES = [
            "auto_backfilled",     # 自动回填，未验证
            "needs_review",        # 明确需要人工审查
            "pending_review",      # 待审查
            "pending_",            # 任何 pending 状态
            "backfill",            # 回填标记
            "unverified",          # 未验证
            "preliminary",         # 初步
            "candidate",           # 本身就是候选
            "stage2",              # 未完成
            "sampled_",            # 抽样
            "closed_by_",          # 已关闭
            "retired_",            # 已退役
            "SELECT",              # SELECT/LENGTH等状态字段
            "INSERT",              # INSERT验证
        ]
        vstat_lower = vstat.lower()
        is_blocked = any(vstat_lower.startswith(prefix.lower()) for prefix in BLOCKED_PREFIXES)

        if is_blocked:
            skipped_reasons[f"blocked_by_gene_inflation_gate_{vstat}"] = skipped_reasons.get(f"blocked_by_gene_inflation_gate_{vstat}", 0) + 1
            continue

        if dry_run:
            promoted += 1
            promoted_ids.append(gid)
            continue

        # 晋升：status='verified', verification='auto_promoted_by_self_evolution_loop'
        evidence = str(row["evidence_grade"] or "B").upper()
        con.execute(
            """
            UPDATE evolution_genes
            SET status = 'verified',
                verification_status = 'auto_promoted_by_self_evolution_loop',
                evidence_grade = ?,
                last_executed = ?
            WHERE gene_id = ? AND status = 'candidate'
            """,
            (evidence, _now(), gid),
        )
        promoted += 1
        promoted_ids.append(gid)

    con.commit()
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/promote",
        "created_at": _now(),
        "dry_run": dry_run,
        "promoted": promoted,
        "promoted_ids": promoted_ids[:20],  # 前20条样例
        "total_candidates_total": len(candidates),
        "skipped_reasons": skipped_reasons,
        "boundary": BOUNDARY,
    }


# ─── Phase 2: 融合（top verified 基因杂交） ───


def run_fusion_on_verified(db_path: Path = DEFAULT_DB, *, dry_run: bool = False) -> dict[str, Any]:
    """对 top-N verified/active 基因运行交叉融合，写入 offspring。

    流程：
    1. 取 top 20 最高 fitness 的 verified/active 基因
    2. 对每对执行 additive + multiplicative 融合
    3. 写入 offspring 到 GeneDB（status=candidate）
    """
    con = _open_db(db_path)

    # 取 top verified/active 基因
    parents = con.execute(
        """
        SELECT gene_id, gene_name, fitness, absorbed_knowledge, source_refs_json,
               evidence_grade, severity_rank
        FROM evolution_genes
        WHERE status IN ('verified', 'active')
          AND absorbed_knowledge IS NOT NULL
          AND absorbed_knowledge LIKE '%signals_match%'
        ORDER BY fitness DESC
        LIMIT ?
        """,
        (FUSION_TOP_N,),
    ).fetchall()

    if len(parents) < 2:
        con.close()
        return {
            "schema": f"{LOOP_VERSION}/fusion",
            "fused": 0,
            "parents_count": len(parents),
            "reason": "not_enough_parents",
            "boundary": BOUNDARY,
        }

    # 读取 absorbed_knowledge 转为 dict
    parent_dicts: list[dict[str, Any]] = []
    for p in parents:
        try:
            d = json.loads(p["absorbed_knowledge"])
            if isinstance(d, dict) and "id" in d:
                parent_dicts.append(d)
        except (json.JSONDecodeError, TypeError):
            continue

    if len(parent_dicts) < 2:
        con.close()
        return {
            "schema": f"{LOOP_VERSION}/fusion",
            "fused": 0,
            "parents_count": len(parents),
            "parsed_parent_dicts": len(parent_dicts),
            "reason": "not_enough_parsed_parents",
            "boundary": BOUNDARY,
        }

    # 融合
    fused_count = 0
    fusion_results: list[dict[str, Any]] = []

    for i in range(len(parent_dicts)):
        for j in range(i + 1, len(parent_dicts)):
            pid_a = parent_dicts[i].get("id", "")
            pid_b = parent_dicts[j].get("id", "")
            if not pid_a or not pid_b:
                continue

            fusion_id = f"auto_fusion_{fusion._hash([pid_a, pid_b])[:16]}"

            # additive
            out_add = fusion.fuse_standard_genes(
                [parent_dicts[i], parent_dicts[j]],
                offspring_id=fusion_id,
                mode="additive",
            )
            add_status = out_add.get("status", "UNKNOWN")
            add_fitness = out_add.get("offspring_gene", {}).get("fitness", 0)

            # 只在非 dry_run 且成功时写入
            if not dry_run and add_status == "PASS" and out_add.get("offspring_gene"):
                ins = fusion.insert_fused_gene(
                    out_add["offspring_gene"],
                    db_path=str(db_path),
                    write=True,
                    promote=False,
                )
                if ins.get("written"):
                    fused_count += 1

            fusion_results.append({
                "parents": [pid_a, pid_b],
                "mode": "additive",
                "status": add_status,
                "fitness": add_fitness,
            })

            # multiplicative
            out_mul = fusion.fuse_standard_genes(
                [parent_dicts[i], parent_dicts[j]],
                offspring_id=fusion_id,
                mode="multiplicative",
            )
            mul_status = out_mul.get("status", "UNKNOWN")
            mul_fitness = out_mul.get("offspring_gene", {}).get("fitness", 0)

            if not dry_run and mul_status == "PASS" and out_mul.get("offspring_gene"):
                ins = fusion.insert_fused_gene(
                    out_mul["offspring_gene"],
                    db_path=str(db_path),
                    write=True,
                    promote=False,
                )
                if ins.get("written"):
                    fused_count += 1

            fusion_results.append({
                "parents": [pid_a, pid_b],
                "mode": "multiplicative",
                "status": mul_status,
                "fitness": mul_fitness,
            })

            # 一次循环最多融合 50 对
            if len(fusion_results) >= 50:
                break
        if len(fusion_results) >= 50:
            break

    con.close()
    return {
        "schema": f"{LOOP_VERSION}/fusion",
        "created_at": _now(),
        "dry_run": dry_run,
        "fused": fused_count,
        "total_pairs_attempted": len(fusion_results),
        "verified_parents_count": len(parent_dicts),
        "pass_count": sum(1 for r in fusion_results if r["status"] == "PASS"),
        "sample_results": fusion_results[:5],
        "boundary": BOUNDARY,
    }


# ─── Phase 3: 基因摄入（扫描代码/吸收外部基因） ───


def run_intake_scan(write_candidates: bool = True, db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    """调用已有 intake loop 扫描代码，产生新 candidate。

    同时自动将 backfilled 但还没写 absorbed_knowledge 的 8-field
    记录补充完整（PGG backfill 有 132 条缺 absorbed_knowledge）。
    """
    # Step 1: 补全 PGG backfill 中缺 absorbed_knowledge 的记录
    con = _open_db(db_path)
    missing = con.execute(
        """
        SELECT gene_id, gene_name, evidence_grade, source_refs_json, severity_rank, boundary
        FROM evolution_genes
        WHERE gene_id LIKE 'pgg_%'
          AND (absorbed_knowledge IS NULL OR absorbed_knowledge = '' OR absorbed_knowledge NOT LIKE '%signals_match%')
        ORDER BY gene_id
        """
    ).fetchall()
    con.close()

    filled = 0
    if missing:
        _log(f"Filling {len(missing)} PGG backfill records with standard template...")
        for row in missing:
            gid = row["gene_id"]
            std_gene = {
                "type": "pgg_gene",
                "id": gid,
                "category": "pgg_backfill",
                "signals_match": ["backfill_gene"],
                "preconditions": ["backfill_source_verified"],
                "strategy": ["use_backfill_strategy"],
                "constraints": {"backfill": True},
                "validation": ["backfill_record_verified"],
            }
            con = _open_db(db_path)
            con.execute(
                "UPDATE evolution_genes SET absorbed_knowledge = ?, evidence_grade = ? WHERE gene_id = ?",
                (json.dumps(std_gene, ensure_ascii=False), str(row["evidence_grade"] or "B").upper(), gid),
            )
            con.commit()
            con.close()
            filled += 1

    # Step 2: 运行 intake loop（若有写候选人模式）
    intake_result = {"status": "skipped", "reason": "no_intake_loop_available"}
    if write_candidates:
        try:
            # 尝试导入并运行
            from agent.pgg_gene_intake_loop import run_intake_loop
            ir = run_intake_loop(write_candidates=True, db_path=str(db_path))
            intake_result = {
                "status": "completed",
                "written": ir.get("written_count", ir.get("candidates_written", 0)),
                "total_scanned": ir.get("total_scanned", 0),
            }
        except Exception as e:
            intake_result = {"status": "error", "error": str(e)}

    return {
        "schema": f"{LOOP_VERSION}/intake",
        "created_at": _now(),
        "pgg_backfill_records_filled": filled,
        "intake_scan": intake_result,
        "boundary": BOUNDARY,
    }


# ─── 汇总报告 ───


def generate_db_summary(db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    """生成 GeneDB 快照摘要 + 健康监控"""
    con = _open_db(db_path)
    total = con.execute("SELECT COUNT(*) FROM evolution_genes").fetchone()[0]
    by_status = dict(con.execute("SELECT status, COUNT(*) FROM evolution_genes GROUP BY status").fetchall())
    by_evidence = dict(con.execute("SELECT evidence_grade, COUNT(*) FROM evolution_genes WHERE evidence_grade IS NOT NULL GROUP BY evidence_grade").fetchall())
    top_fitness = con.execute("SELECT gene_id, status, fitness, verification_status FROM evolution_genes ORDER BY fitness DESC LIMIT 10").fetchall()
    
    # 健康监控指标
    verified_count = by_status.get('verified', 0)
    candidate_count = by_status.get('candidate', 0)
    active_count = by_status.get('active', 0)
    retired_count = by_status.get('retired', 0)
    
    # fitness 健康扫描
    low_fitness_verified = con.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE status='verified' AND (fitness IS NULL OR fitness < 500)"
    ).fetchone()[0]
    has_fitness = con.execute("SELECT COUNT(*) FROM evolution_genes WHERE fitness IS NOT NULL").fetchone()[0]
    avg_fitness = None
    if has_fitness > 0:
        avg_fitness = round(con.execute("SELECT AVG(fitness) FROM evolution_genes WHERE fitness IS NOT NULL").fetchone()[0], 1)
    
    # 退化信号：verified持续下降、candidate堆积不晋升、low-fitness verified
    health_signals = []
    if verified_count < 20:
        health_signals.append(f"VERIFIED_LOW({verified_count})")
    if candidate_count > total * 0.8:
        health_signals.append(f"CANDIDATE_STAGNATION({candidate_count}/{total})")
    if low_fitness_verified > 5:
        health_signals.append(f"LOW_FITNESS_VERIFIED({low_fitness_verified})")
    if retired_count > active_count:
        health_signals.append(f"RETIRE_EXCEEDS_ACTIVE({retired_count}>{active_count})")
    
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/summary",
        "created_at": _now(),
        "total_genes": total,
        "by_status": {k: v for k, v in sorted(by_status.items())},
        "by_evidence": {k: v for k, v in sorted(by_evidence.items())},
        "health": {
            "verified_score": round(verified_count / max(total, 1) * 100, 1),
            "avg_fitness": avg_fitness,
            "low_fitness_verified": low_fitness_verified,
            "verified_to_candidate_ratio": round(verified_count / max(candidate_count, 1), 3),
            "signals": health_signals if health_signals else None,
        },
        "top_fitness": [
            {"gene_id": r[0], "status": r[1], "fitness": r[2], "verification": r[3]}
            for r in top_fitness
        ],
        "boundary": BOUNDARY,
    }


# ─── 主入口：一键运行全部 ───


def run_evolution_cycle(*, promote: bool = True, fusion: bool = True, intake: bool = True,
                        dream_mode: bool = True, aris_reflect: bool = True, 
                        picoapex_check: bool = True, health_check: bool = True,
                        dry_run: bool = False, db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    """运行一次完整的自主演化周期。

    Args:
        promote: 是否执行晋升（candidate→verified）
        fusion: 是否执行融合（verified→offspring）
        intake: 是否执行基因摄入（扫描代码/补全 backfill）
        dream_mode: 是否执行梦境合成（回顾→合成→模拟→写入）
        aris_reflect: 是否执行3层反思（偏差→逻辑→架构）
        picoapex_check: 是否执行饱和检测+目标切换
        health_check: 是否执行健康监控采集
        dry_run: 只读模式（不写 DB）
        db_path: GeneDB 路径
    """
    _log(f"=== PGG 自主演化闭环开始 (dry_run={dry_run}) ===")
    start = time.time()

    result: dict[str, Any] = {
        "schema": f"{LOOP_VERSION}/full_cycle",
        "created_at": _now(),
        "dry_run": dry_run,
        "phases": {},
        "duration_seconds": 0,
        "boundary": BOUNDARY,
    }

    # Phase 1: 摄入
    if intake:
        _log("Phase 1: 基因摄入/补全...")
        intake_result = run_intake_scan(write_candidates=not dry_run, db_path=db_path)
        result["phases"]["intake"] = intake_result
        _log(f"  → intake: {json.dumps(intake_result, ensure_ascii=False)}")

    # Phase 2: 晋升
    if promote:
        _log("Phase 2: 晋升 candidate 基因...")
        promo_result = promote_candidates(db_path, dry_run=dry_run)
        result["phases"]["promote"] = promo_result
        _log(f"  → promoted: {promo_result['promoted']}")

    # Phase 3: 融合
    if fusion:
        _log("Phase 3: 基因融合（top verified → offspring）...")
        fusion_result = run_fusion_on_verified(db_path, dry_run=dry_run)
        result["phases"]["fusion"] = fusion_result
        _log(f"  → fused: {fusion_result['fused']} new offspring")

# Phase 4: 3层ARIS反思
    if aris_reflect:
        _log("Phase 4: ARIS 3层反思（偏差/逻辑/架构边界）...")
        try:
            reflector = aris.ArisReflector()
            aris_result = reflector.run_reflection()
            result["phases"]["aris_reflection"] = aris_result
            _log(f"  → L1偏差={aris_result.get('l1_score')}, L2问题={len(aris_result.get('l2_issues', []))}, L3阻塞={len(aris_result.get('l3_blockers', []))}")
        except Exception as e:
            _log(f"  → ARIS 反思失败: {e}")
            result["phases"]["aris_reflection"] = {"error": str(e)}

    # Phase 5: 梦境合成
    if dream_mode and not dry_run:
        _log("Phase 5: 基因梦境合成（回顾/融合/模拟/写入）...")
        try:
            engine = dream.DreamEngine()
            dream_result = engine.run_full_cycle()
            result["phases"]["dream_mode"] = dream_result
            _log(f"  → 合成 {dream_result.get('synth_count', 0)} 个新基因")
        except Exception as e:
            _log(f"  → 梦境合成失败: {e}")
            result["phases"]["dream_mode"] = {"error": str(e)}

    # Phase 6: PicoAPEX 饱和检测 + 自动目标切换
    if picoapex_check:
        _log("Phase 6: PicoAPEX 饱和检测...")
        try:
            pico = picoapex.PicoAPEXEngine()
            pico_result = pico.check_and_switch()
            result["phases"]["picoapex"] = pico_result
            _log(f"  → 维度={pico_result.get('current_dim')}, 精英率={pico_result.get('elite_ratio'):.4f}, 饱和={pico_result.get('saturated')}")
        except Exception as e:
            _log(f"  → PicoAPEX 失败: {e}")
            result["phases"]["picoapex"] = {"error": str(e)}

    # Phase 7: 健康监控
    if health_check:
        _log("Phase 7: 健康监控采集...")
        try:
            monitor = health.HealthMonitor()
            health_result = monitor.collect_and_report()
            result["phases"]["health"] = health_result.get("status", "OK")
            _log(f"  → 健康级别={health_result.get('level', 'unknown')}, 告警={len(health_result.get('alerts', []))}条")
        except Exception as e:
            _log(f"  → 健康监控失败: {e}")
            result["phases"]["health"] = {"error": str(e)}

    # Summary
    summary = generate_db_summary(db_path)
    result["summary"] = summary
    result["duration_seconds"] = round(time.time() - start, 2)

    _log(f"=== PGG 自主演化闭环完成 ({result['duration_seconds']}s) ===")
    _log(f"  总基因数: {summary['total_genes']}")
    _log(f"  status 分布: {summary['by_status']}")
    _log(f"  evidence 分布: {summary['by_evidence']}")

    return result


# ─── CLI 入口 ───


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PGG 自主演化闭环")
    parser.add_argument("--dry-run", "-n", action="store_true", help="只读模式，不写 DB")
    parser.add_argument("--no-promote", action="store_true", help="跳过晋升阶段")
    parser.add_argument("--no-fusion", action="store_true", help="跳过融合阶段")
    parser.add_argument("--no-intake", action="store_true", help="跳过摄入阶段")
    parser.add_argument("--promote-only", action="store_true", help="只执行晋升")
    parser.add_argument("--summary", action="store_true", help="只显示当前 DB 摘要")
    args = parser.parse_args()

    if args.summary:
        s = generate_db_summary()
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return

    result = run_evolution_cycle(
        promote=not args.no_promote and not args.promote_only or args.promote_only,
        fusion=not args.no_fusion and not args.promote_only,
        intake=not args.no_intake and not args.promote_only,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()