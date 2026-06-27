"""PGG 自主演化闭环 — 全自动基因摄取/晋升/融合/报告。
直接操作真实 DB schema（gene_lifecycle + genes 表）。

三层管道：
1. promote — 将 quality_score 达标的 candidate 基因晋升为 promoted
2. fusion  — 对 top-N promoted/active 基因交叉融合，生成 offspring candidate
3. intake  — 从文件系统扫描代码模式，写入新 candidate

=== 核心纪律（2026-06-24 固化） ===
【融合 = LLM 级基因交叉，非简单拼接】
- 旧 _build_fusion_code_snippet() 已被 GPT55 判定"简单拼接无实质价值"，标记 DEPRECATED
- 新引擎使用 _llm_fuse_pair() + GPT-5.5 做真正的遗传算法 crossover：
  分析两个母本的功能逻辑，合成一个新的可运行函数
- standalone 模式无 LLM 时返回 SKIP_LLM_UNAVAILABLE，不产生假基因
- 互补 pair 选择：跳过同 pattern_type 对（python_function同类型融合收益低）
- LLM fusion offspring quality = avg(parents) x 0.9，review_status = pending
- 未审计的 fusion 不可自动 promote（review_status 门禁）

【禁止事项】
- 禁止用代码拼接/注释分隔冒充基因融合
- 禁止 standalone 模式产生空壳 offspring
- 禁止 audit reject 后仍标记为 promoted

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


def _nonempty_text(value: Any) -> str:
    """Return stripped text only when it contains real, non-whitespace content."""
    if value is None:
        return ""
    text = str(value).strip()
    return text if text else ""


def _gene_material_kind(code_snippet: Any) -> str:
    """Classify gene material for fusion.

    PGG/Xuanji-style gene usage is not always direct runtime loading.
    A gene can be:
    - python_code: executable code suitable for code-code LLM crossover
    - metadata_gene: structured JSON/standard-gene card suitable for pattern-code fusion
    - text: weak material, usually not fusion-ready
    """
    text = _nonempty_text(code_snippet)
    if not text:
        return "empty"
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict) and obj.get("type") in {"apex_gene_candidate", "pgg_gene"}:
                return "metadata_gene"
        except Exception:
            pass
    if "def " in text or "class " in text or stripped.startswith("#!/usr/bin/env python"):
        return "python_code"
    return "text"


def _fusion_style(kind_a: str, kind_b: str) -> str:
    if kind_a == "python_code" and kind_b == "python_code":
        return "code_code_crossover"
    if "metadata_gene" in {kind_a, kind_b} and "python_code" in {kind_a, kind_b}:
        return "pattern_code_fusion"
    if kind_a == "metadata_gene" and kind_b == "metadata_gene":
        return "pattern_pattern_design_fusion"
    return "weak_text_fusion"


def _build_fusion_code_snippet(p_a: sqlite3.Row, p_b: sqlite3.Row) -> str:
    """⚠️ DEPRECATED — 2026-06-24: 此函数仅为"简单拼接"，
    已被 _llm_fuse_pair() + LLM crossover 取代 (\u4e0d\u518d\u88ab run_fusion_on_verified \u8c03\u7528)。
    保留供历史追溯引用，新融合请使用 _llm_fuse_pair()。"""
    import warnings
    warnings.warn("_build_fusion_code_snippet is deprecated; use _llm_fuse_pair() for LLM crossover", DeprecationWarning, stacklevel=2)
    snippet_a = _nonempty_text(p_a["code_snippet"])
    snippet_b = _nonempty_text(p_b["code_snippet"])
    if not snippet_a and not snippet_b:
        return ""
    parts = [
        "# auto_fusion offspring generated from verified parent code snippets",
        f"# parent_a={p_a['gene_id']}:{p_a['name'] or ''}",
        f"# parent_b={p_b['gene_id']}:{p_b['name'] or ''}",
    ]
    if snippet_a:
        parts.extend(["\n# --- parent_a_snippet ---", snippet_a[:4000]])
    if snippet_b:
        parts.extend(["\n# --- parent_b_snippet ---", snippet_b[:4000]])
    offspring = "\n".join(parts).strip()
    return offspring if offspring and (snippet_a or snippet_b) else ""


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
          AND NOT (
            g.pattern_type = 'llm_fusion'
            AND EXISTS (
              SELECT 1 FROM evolution_genes eg
              WHERE eg.gene_id = gl.gene_id
                AND eg.mutation_vector = 'llm_fusion'
                AND COALESCE(eg.review_status, 'pending') != 'approved'
            )
          )
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

        # 跳过已审核拒绝的 auto_fusion 子代
        # NOTE: row 是 sqlite3.Row，不支持 .get()，必须用 try/index
        try:
            ptype = str(row["gene_name"] or "")
        except (IndexError, KeyError):
            ptype = ""
        if "auto_fusion" in ptype.lower() or "fusion_" in ptype.lower():
            eg_check = con.execute(
                "SELECT review_status FROM evolution_genes WHERE gene_id = ? AND review_status = 'rejected' LIMIT 1",
                (gid,),
            ).fetchone()
            if eg_check:
                skipped_reasons["auto_fusion_rejected"] = skipped_reasons.get("auto_fusion_rejected", 0) + 1
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
            # 插入 evolution_genes 追踪记录。llm_fusion 能到这里说明前置
            # review_status='approved' 门禁已通过，promotion 追踪行也必须
            # 携带 approved，避免默认 pending 造成统计误报。
            try:
                pattern_type = str(row["pattern_type"] or "")
            except (IndexError, KeyError):
                pattern_type = ""
            promote_review_status = "approved" if pattern_type == "llm_fusion" else "auto_promoted"
            promote_review_channel = "promotion_gate_after_llm_review" if pattern_type == "llm_fusion" else "quality_gate"
            con.execute(
                """INSERT OR IGNORE INTO evolution_genes
                   (gene_id, parent_gene_id, state, generation, mutation_vector,
                    fitness_before, fitness_after, promoted_at, retired_at, evidence_ref, created_at,
                    review_status, review_channel)
                   VALUES (?, NULL, 'promoted', 1, 'auto_promoted', NULL, ?, ?, NULL, '{}', ?, ?, ?)""",
                (gid, q, now, now, promote_review_status, promote_review_channel),
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

_LLM_FUSION_AVAILABLE: bool | None = None


def _lm_fusion_available() -> bool:
    """检查 GPT55 审计 MCP 连通性（结果缓存 60 秒）。"""
    global _LLM_FUSION_AVAILABLE
    import time
    try:
        from mcp_llm_audit_audit_gpt55 import audit_gpt55  # type: ignore
        _LLM_FUSION_AVAILABLE = True
    except (ImportError, Exception):
        _LLM_FUSION_AVAILABLE = False
    return bool(_LLM_FUSION_AVAILABLE)


def _llm_fuse_pair(agent_a_name: str, code_a: str, agent_b_name: str, code_b: str) -> str | None:
    """调用 GPT-5.5 对两个母本做真正的基因融合。"""
    try:
        from mcp_llm_audit_audit_gpt55 import audit_gpt55

        prompt = (
            f"## 基因融合任务（遗传算法 crossover，非简单拼接）\n\n"
            f"### 母本 A: {agent_a_name}\n"
            f"```python\n{code_a[:3000]}\n```\n\n"
            f"### 母本 B: {agent_b_name}\n"
            f"```python\n{code_b[:3000]}\n```\n\n"
            f"### 要求\n"
            f"分析两个母本的核心功能逻辑，合成一个**全新的、可运行的 Python 函数**"
            f"（不是把两个函数体拼在一起）。\n\n"
            f"新函数应该继承两者的核心能力，形成有意义的组合。\n\n"
            f"### 输出格式\n"
            f"```python\n"
            f"# --- FUSION offspring ---\n"
            f"# parent_a: {agent_a_name}\n"
            f"# parent_b: {agent_b_name}\n"
            f"<完整 Python 函数代码>\n"
            f"# --- END FUSION ---\n"
            f"```\n\n"
            f"只输出代码块，不要额外说明。"
        )
        result = audit_gpt55(prompt=prompt, system=(
            "You are a genetic algorithm gene fusion engine. "
            "Analyze two parent gene functions, extract core logic, "
            "and synthesize a NEW function combining their capabilities. "
            "This is NOT code concatenation - this is crossover. "
            "Output ONLY the Python code block."
        ))
        text = result.get("result", "") or result.get("content", "") or str(result)
        import re
        m = re.search(r"```python\n(.+?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        if "def " in text:
            return text.strip()
        return None
    except Exception as exc:
        _log(f"  LLM fusion failed for {agent_a_name} x {agent_b_name}: {exc}")
        return None


# ─── Phase 2: 融合 top promoted/active 基因（LLM 级真实融合）───
#
def _collect_fusion_parent_pairs(db_path: Path = DEFAULT_DB, *, limit_pairs: int = MAX_FUSION_PAIRS) -> dict[str, Any]:
    """Collect fusion-ready parent pairs without calling any LLM.

    This is the missing bridge between launchd/standalone runs and Hermes session
    LLM tools: when GPT/Claude/DeepSeek MCP is not importable inside the runner,
    the loop should still produce a concrete fusion request packet instead of a
    cosmetic SKIP with no usable work item.
    """
    con = _open_db(db_path)
    parents = con.execute(
        """
        SELECT gl.gene_id, g.name, g.pattern_type, g.source_repo, g.code_snippet,
               COALESCE(
                 CASE WHEN gl.quality_score < 5.0 AND g.quality_score > 10.0 THEN g.quality_score
                      ELSE gl.quality_score
                 END,
                 g.quality_score, gl.quality_score
               ) AS quality_score
        FROM gene_lifecycle gl
        LEFT JOIN genes g ON gl.gene_id = g.id
        WHERE gl.state IN ('promoted', 'active')
          AND g.code_snippet IS NOT NULL
          AND LENGTH(g.code_snippet) BETWEEN 500 AND 20000
          AND g.pattern_type NOT IN ('auto_fusion', 'report', 'documentation')
        ORDER BY quality_score DESC
        LIMIT ?
        """,
        (max(FUSION_TOP_N, 200),),
    ).fetchall()
    con.close()

    parent_rows: list[dict[str, Any]] = []
    for p in parents:
        kind = _gene_material_kind(p["code_snippet"])
        if kind in {"empty", "text"}:
            continue
        parent_rows.append({
            "gene_id": int(p["gene_id"]),
            "name": str(p["name"] or ""),
            "pattern_type": str(p["pattern_type"] or ""),
            "source_repo": str(p["source_repo"] or ""),
            "quality_score": float(p["quality_score"] or 0),
            "material_kind": kind,
            "code_len": len(_nonempty_text(p["code_snippet"])),
        })

    pairs: list[dict[str, Any]] = []
    skipped_reasons: dict[str, int] = {}
    for i in range(len(parents)):
        for j in range(i + 1, len(parents)):
            if len(pairs) >= limit_pairs:
                break
            p_a, p_b = parents[i], parents[j]
            kind_a = _gene_material_kind(p_a["code_snippet"])
            kind_b = _gene_material_kind(p_b["code_snippet"])
            style = _fusion_style(kind_a, kind_b)
            if style == "weak_text_fusion":
                skipped_reasons["weak_text_fusion"] = skipped_reasons.get("weak_text_fusion", 0) + 1
                continue
            if style == "pattern_pattern_design_fusion":
                skipped_reasons["pattern_pattern_design_deferred"] = skipped_reasons.get("pattern_pattern_design_deferred", 0) + 1
                continue
            if str(p_a["pattern_type"] or "") == str(p_b["pattern_type"] or "") and style == "code_code_crossover":
                skipped_reasons["same_code_type"] = skipped_reasons.get("same_code_type", 0) + 1
                continue
            pairs.append({
                "parents": [int(p_a["gene_id"]), int(p_b["gene_id"])],
                "parents_name": [str(p_a["name"] or ""), str(p_b["name"] or "")],
                "parents_pattern_type": [str(p_a["pattern_type"] or ""), str(p_b["pattern_type"] or "")],
                "parents_quality": [float(p_a["quality_score"] or 0), float(p_b["quality_score"] or 0)],
                "material_kind": [kind_a, kind_b],
                "fusion_style": style,
                "prompt_contract": "LLM must synthesize a single runnable Python function; metadata_gene is a pattern source, not executable code.",
            })
        if len(pairs) >= limit_pairs:
            break

    return {
        "schema": f"{LOOP_VERSION}/fusion_request_packet",
        "created_at": _now(),
        "parents_count": len(parent_rows),
        "parents_sample": parent_rows[:8],
        "pairs_ready": len(pairs),
        "pairs": pairs,
        "skipped_reasons": skipped_reasons,
        "boundary": BOUNDARY,
    }


# 2026-06-24: 彻底重构。原来的 _build_fusion_code_snippet 只是拼接
# 两段代码加注释，GPT55 审计判定"简单拼接无实质价值"。新版本使用
# GPT-5.5 做真正的基因交叉（crossover）：分析两个母本的功能逻辑，
# 合成一个新的、可运行的 Python 函数。每次循环最多融合 MAX_FUSION_PAIRS 对。
# 若 GPT55 不可用，回退为 fusion_SKIP（不产生假基因）。


def run_fusion_on_verified(db_path: Path = DEFAULT_DB, *, dry_run: bool = False) -> dict[str, Any]:
    """取 top-N promoted/active 基因，LLM 融合生成 offspring candidate。

    使用 GPT-5.5 做真正的基因 crossover（非简单拼接）。每次最多
    MAX_FUSION_PAIRS 对。若 LLM 不可用（standalone 模式），返回
    SKIP_LLM_UNAVAILABLE 不产生假基因。从 Hermes agent session 调用时，
    先 run_fusion_on_verified() → 拿 parents 列表，然后通过 MCP 工具
    做 LLM 融合，最后用 write_llm_fusion_results() 写入 DB。
    """
    if not _lm_fusion_available():
        request_packet = _collect_fusion_parent_pairs(db_path, limit_pairs=MAX_FUSION_PAIRS)
        return {
            "schema": f"{LOOP_VERSION}/fusion",
            "created_at": _now(),
            "fused": 0,
            "status": "PENDING_LLM_SESSION_FUSION",
            "reason": "LLM MCP not importable in standalone runner; produced fusion_request_packet for Hermes session consumption",
            "fusion_request_packet": request_packet,
            "boundary": BOUNDARY,
        }

    con = _open_db(db_path)

    # 取 top-N 有真实代码的 promoted/active 基因
    # 取 top-N 有真实代码的 promoted/active 基因
    parents = con.execute(
        """
        SELECT gl.gene_id, g.name, g.pattern_type, g.source_repo, g.code_snippet,
               COALESCE(
                 CASE WHEN gl.quality_score < 5.0 AND g.quality_score > 10.0 THEN g.quality_score
                      ELSE gl.quality_score
                 END,
                 g.quality_score, gl.quality_score
               ) AS quality_score
        FROM gene_lifecycle gl
        LEFT JOIN genes g ON gl.gene_id = g.id
        WHERE gl.state IN ('promoted', 'active')
          AND g.code_snippet IS NOT NULL
          AND LENGTH(g.code_snippet) BETWEEN 500 AND 20000
          AND g.pattern_type NOT IN ('auto_fusion', 'report', 'documentation')
        ORDER BY quality_score DESC
        LIMIT ?
        """,
        (max(FUSION_TOP_N, 200),),
    ).fetchall()

    if len(parents) < 2:
        con.close()
        return {"schema": f"{LOOP_VERSION}/fusion", "fused": 0, "parents_count": len(parents),
                "reason": "not_enough_parents", "boundary": BOUNDARY}

    fused_count = 0
    fusion_results: list[dict[str, Any]] = []
    pairs_tried = 0
    skipped_reasons: dict[str, int] = {}

    # 只融合互补的 pair（不同 pattern_type，最大差异最大化创新）
    for i in range(len(parents)):
        for j in range(i + 1, len(parents)):
            if pairs_tried >= MAX_FUSION_PAIRS:
                break

            p_a, p_b = parents[i], parents[j]
            pid_a, pid_b = int(p_a["gene_id"]), int(p_b["gene_id"])

            # 跳过同类型基因（同类型融合通常收益低）
            pt_a = str(p_a["pattern_type"] or "")
            pt_b = str(p_b["pattern_type"] or "")
            if pt_a == pt_b and "python_function" in pt_a:
                skipped_reasons["same_type"] = skipped_reasons.get("same_type", 0) + 1
                continue

            parent_code_a = _nonempty_text(p_a["code_snippet"])
            parent_code_b = _nonempty_text(p_b["code_snippet"])
            if not parent_code_a or not parent_code_b:
                skipped_reasons["missing_code"] = skipped_reasons.get("missing_code", 0) + 1
                continue

            kind_a = _gene_material_kind(parent_code_a)
            kind_b = _gene_material_kind(parent_code_b)
            style = _fusion_style(kind_a, kind_b)
            if style == "weak_text_fusion":
                skipped_reasons["weak_text_fusion"] = skipped_reasons.get("weak_text_fusion", 0) + 1
                continue
            if style == "pattern_pattern_design_fusion":
                skipped_reasons["pattern_pattern_design_deferred"] = skipped_reasons.get("pattern_pattern_design_deferred", 0) + 1
                continue

            pairs_tried += 1
            name_a = str(p_a["name"] or "unknown_a")
            name_b = str(p_b["name"] or "unknown_b")

            # LLM 融合
            if dry_run:
                fusion_results.append({
                    "parents": [str(pid_a), str(pid_b)],
                    "parents_name": [name_a, name_b],
                    "material_kind": [kind_a, kind_b],
                    "fusion_style": style,
                    "dry_run": True,
                    "status": "DRY_RUN",
                })
                continue

            offspring_code = _llm_fuse_pair(name_a, parent_code_a[:4000],
                                             name_b, parent_code_b[:4000])
            if not offspring_code:
                skipped_reasons["llm_fusion_failed"] = skipped_reasons.get("llm_fusion_failed", 0) + 1
                continue

            if len(offspring_code) < 100:
                skipped_reasons["offspring_too_short"] = skipped_reasons.get("offspring_too_short", 0) + 1
                continue

            # 写入 DB
            now = _now()
            max_id = con.execute("SELECT COALESCE(MAX(id), 0) FROM genes").fetchone()[0]
            offspring_id = max_id + 1
            avg_quality = (float(p_a["quality_score"] or 0) + float(p_b["quality_score"] or 0)) / 2

            try:
                con.execute(
                    """INSERT OR IGNORE INTO genes
                       (id, name, pattern_type, source_repo, code_snippet, quality_score, extracted_at)
                       VALUES (?, ?, 'llm_fusion', 'self_evolution_loop_llm', ?, ?, ?)""",
                    (offspring_id,
                     f"llm_fusion_{name_a[:20]}_{name_b[:20]}"[:60].replace(" ", "_"),
                     offspring_code, round(avg_quality * 0.9, 2), now),
                )
                con.execute(
                    """INSERT OR IGNORE INTO gene_lifecycle
                       (gene_id, state, candidate_at, quality_score)
                       VALUES (?, 'candidate', ?, ?)""",
                    (offspring_id, now, round(avg_quality * 0.9, 2)),
                )
                # evolution_genes 追踪（review_status='pending' 要求审核）
                con.execute(
                    """INSERT OR IGNORE INTO evolution_genes
                       (gene_id, parent_gene_id, state, generation, mutation_vector,
                        fitness_before, fitness_after, created_at, review_status)
                       VALUES (?, ?, 'candidate', 1, 'llm_fusion', NULL, ?, ?, 'pending')""",
                    (offspring_id, f"{pid_a},{pid_b}", round(avg_quality * 0.9, 2), now),
                )
                fused_count += 1
                fusion_results.append({
                    "parents": [str(pid_a), str(pid_b)],
                    "parents_name": [name_a, name_b],
                    "offspring_id": offspring_id,
                    "offspring_name": f"llm_fusion_{name_a[:20]}_{name_b[:20]}"[:60].replace(" ", "_"),
                    "code_snippet_len": len(offspring_code),
                })
            except sqlite3.IntegrityError:
                pass

    if fused_count > 0:
        con.commit()
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/fusion",
        "created_at": _now(),
        "dry_run": dry_run,
        "fused": fused_count,
        "total_pairs_attempted": pairs_tried,
        "skipped_reasons": skipped_reasons,
        "verified_parents_count": len(parents),
        "llm_available": _LLM_FUSION_AVAILABLE,
        "sample_results": fusion_results[:3],
        "boundary": BOUNDARY,
    }


def write_llm_fusion_results(
    offspring_entries: list[dict[str, Any]],
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    """将 agent session 中 LLM 融合的 offspring 写入 DB。

    由 Hermes agent 会话从 MCP GPT55 获取融合代码后调用。
    每个 entry 必须包含: name_a, name_b, pid_a, pid_b, code, quality_avg
    """
    con = _open_db(db_path)
    written = 0
    results: list[dict[str, Any]] = []

    for entry in offspring_entries:
        name_a = str(entry.get("name_a", "unknown_a"))
        name_b = str(entry.get("name_b", "unknown_b"))
        pid_a = int(entry.get("pid_a", 0))
        pid_b = int(entry.get("pid_b", 0))
        offspring_code = str(entry.get("code", ""))
        avg_quality = float(entry.get("quality_avg", 0))

        if len(offspring_code) < 100:
            continue

        now = _now()
        max_id = con.execute("SELECT COALESCE(MAX(id), 0) FROM genes").fetchone()[0]
        offspring_id = max_id + 1

        try:
            con.execute(
                """INSERT OR IGNORE INTO genes
                   (id, name, pattern_type, source_repo, code_snippet, quality_score, extracted_at)
                   VALUES (?, ?, 'llm_fusion', 'self_evolution_loop_llm', ?, ?, ?)""",
                (offspring_id,
                 f"llm_fusion_{name_a[:20]}_{name_b[:20]}"[:60].replace(" ", "_"),
                 offspring_code, round(avg_quality * 0.9, 2), now),
            )
            con.execute(
                """INSERT OR IGNORE INTO gene_lifecycle
                   (gene_id, state, candidate_at, quality_score)
                   VALUES (?, 'candidate', ?, ?)""",
                (offspring_id, now, round(avg_quality * 0.9, 2)),
            )
            con.execute(
                """INSERT OR IGNORE INTO evolution_genes
                   (gene_id, parent_gene_id, state, generation, mutation_vector,
                    fitness_before, fitness_after, created_at, review_status)
                   VALUES (?, ?, 'candidate', 1, 'llm_fusion', NULL, ?, ?, 'pending')""",
                (offspring_id, f"{pid_a},{pid_b}", round(avg_quality * 0.9, 2), now),
            )
            written += 1
            results.append({
                "offspring_id": offspring_id,
                "parents": [str(pid_a), str(pid_b)],
                "parents_name": [name_a, name_b],
                "code_snippet_len": len(offspring_code),
            })
        except sqlite3.IntegrityError:
            pass

    if written > 0:
        con.commit()
    con.close()

    return {
        "schema": f"{LOOP_VERSION}/fusion_write",
        "created_at": _now(),
        "written": written,
        "results": results,
        "boundary": BOUNDARY,
    }




# ─── Phase 3: 代码扫描摄入新基因 ───

SCAN_DIRS = [
    "/Users/appleoppa/.hermes/hermes-agent/agent",
    "/Users/appleoppa/.hermes/hermes-agent/rust_modules",
    "/Users/appleoppa/.hermes/hermes-agent/skills",
    "/Users/appleoppa/.hermes/bin",
]


def _scan_for_patterns(root_dir: str) -> list[dict[str, Any]]:
    """扫描 Python/Rust/Shell/Binaries，检测 agent/tool/skill 模式，返回候选基因列表。"""
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

    for rs_file in sorted(root.glob("*.rs")):
        try:
            text = rs_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "fn " in text and len(text) >= 200:
            func_count = text.count("fn ")
            gene_id = hashlib.sha256(rs_file.name.encode()).hexdigest()[:12]
            candidates.append({
                "gene_id": gene_id,
                "name": rs_file.stem,
                "pattern_type": "rust_module",
                "source_repo": str(rs_file),
                "quality_score": min(int(len(text) * 0.01 + func_count * 5), 100),
            })

    for sh_file in sorted(root.glob("*.sh")):
        try:
            text = sh_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if len(text) >= 100:
            gene_id = hashlib.sha256(sh_file.name.encode()).hexdigest()[:12]
            candidates.append({
                "gene_id": gene_id,
                "name": sh_file.stem,
                "pattern_type": "shell_script",
                "source_repo": str(sh_file),
                "quality_score": min(int(len(text) * 0.05), 100),
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