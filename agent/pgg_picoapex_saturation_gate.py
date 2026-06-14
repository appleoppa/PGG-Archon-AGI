#!/usr/bin/env python3
"""PicoAPEX 实时饱和度检测门禁。

边界：internal PGG gate; local computation only; no LLM/network; no AGI/T5/ASI claim。
本模块只读取本机 PGG 基因库 SQLite/JSON 状态，不调用模型、不访问网络、不声明 AGI/T5/ASI 能力。
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

# 中文注释：当前 PGG Archon 基因库默认位置；可用环境变量覆盖，便于测试与迁移。
DEFAULT_GENE_DB = Path(
    os.environ.get(
        "PGG_GENE_DB",
        "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3",
    )
)
DEFAULT_STATE_PATH = Path(
    os.environ.get("PGG_PICOAPEX_STATE", "/Users/appleoppa/.hermes/data/self-evolution-loop/latest.json")
)

SCHEMA = "pgg.picoapex.saturation_gate.v1"
BOUNDARY = "internal PGG gate; local computation only; no LLM/network; no AGI/T5/ASI claim"
DIMENSION_CYCLE = ["cognition", "reasoning", "planning", "coding", "analysis"]
SATURATION_THRESHOLD_PCT = 98.0
# 中文注释：elite 判定优先使用 fitness；若库内 fitness 量纲变化，可通过环境变量覆盖。
ELITE_FITNESS_THRESHOLD = float(os.environ.get("PGG_ELITE_FITNESS_THRESHOLD", "800"))
ACTIVE_STATUSES = {"active", "verified"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _as_text(value: Any) -> str:
    """中文注释：把任意本地字段转成可分类文本，不做外部调用。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _next_dimension(current: str) -> str:
    """中文注释：按 cognition → reasoning → planning → coding → analysis → cognition 循环。"""
    try:
        idx = DIMENSION_CYCLE.index(current)
    except ValueError:
        idx = 0
    return DIMENSION_CYCLE[(idx + 1) % len(DIMENSION_CYCLE)]


def _detect_dimension(row: dict[str, Any]) -> str:
    """从基因字段中做本地关键词归类，缺省归入 cognition。"""
    text = " ".join(
        _as_text(row.get(key)).lower()
        for key in (
            "dimension",
            "domain",
            "skill",
            "gate_type",
            "gene_name",
            "defect_name",
            "repair_mechanism",
            "reusable_rule",
            "apex_variables",
            "absorbed_knowledge",
            "boundary",
        )
    )
    keyword_map = {
        "coding": (
            "coding",
            "code",
            "python",
            "pytest",
            "script",
            "module",
            "cli",
            "编程",
            "代码",
            "测试",
            "修复",
        ),
        "planning": (
            "planning",
            "plan",
            "scheduler",
            "cron",
            "roadmap",
            "workflow",
            "pipeline",
            "计划",
            "规划",
            "调度",
        ),
        "reasoning": (
            "reasoning",
            "logic",
            "inference",
            "deduction",
            "proof",
            "gate",
            "verify",
            "推理",
            "逻辑",
            "证明",
            "核验",
        ),
        "analysis": (
            "analysis",
            "analyze",
            "audit",
            "metric",
            "benchmark",
            "reflection",
            "observe",
            "分析",
            "审计",
            "指标",
            "观测",
            "反思",
        ),
        "cognition": (
            "cognition",
            "memory",
            "knowledge",
            "learn",
            "gene",
            "skill",
            "认知",
            "记忆",
            "知识",
            "学习",
            "基因",
        ),
    }
    for dim in ("reasoning", "planning", "coding", "analysis", "cognition"):
        if any(token in text for token in keyword_map[dim]):
            return dim
    return "cognition"


def _select_columns(con: sqlite3.Connection) -> list[str]:
    rows = con.execute("PRAGMA table_info(evolution_genes)").fetchall()
    return [str(row[1]) for row in rows]


def _read_gene_rows(db_path: Path) -> tuple[list[dict[str, Any]], str | None]:
    """读取当前基因库；失败时返回空列表和错误字符串，保证 CLI 有 JSON 输出。"""
    if not db_path.exists():
        return [], f"GeneDB not found: {db_path}"
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        try:
            columns = _select_columns(con)
            if not columns:
                return [], "evolution_genes table not found or has no columns"
            select_cols = ", ".join(f'"{c}"' for c in columns)
            rows = con.execute(f"SELECT {select_cols} FROM evolution_genes").fetchall()
            return [dict(row) for row in rows], None
        finally:
            con.close()
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def _current_dimension(state: dict[str, Any], metrics: dict[str, dict[str, Any]]) -> str:
    """优先读取本地状态；否则选择最接近饱和且样本非空的维度。"""
    candidates: list[Any] = [
        state.get("current_dimension"),
        state.get("current_dim"),
        state.get("target_dimension"),
        state.get("dimension"),
    ]
    for key in ("picoapex", "picoapex_goal", "goal", "target"):
        nested = state.get(key)
        if isinstance(nested, dict):
            candidates.extend(
                [nested.get("current_dimension"), nested.get("current_dim"), nested.get("target_dimension"), nested.get("dimension")]
            )
    for item in candidates:
        if isinstance(item, str) and item in DIMENSION_CYCLE:
            return item

    non_empty = [dim for dim in DIMENSION_CYCLE if metrics.get(dim, {}).get("total", 0) > 0]
    if not non_empty:
        return DIMENSION_CYCLE[0]
    return max(non_empty, key=lambda dim: (metrics[dim]["elite_pct"], metrics[dim]["total"]))


def _compute_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """中文注释：按维度计算 elite%，即 elite_count / total_count * 100。"""
    metrics: dict[str, dict[str, Any]] = {
        dim: {"total": 0, "elite": 0, "elite_pct": 0.0, "active": 0, "recent_elite_pct": None, "older_elite_pct": None}
        for dim in DIMENSION_CYCLE
    }
    dated: dict[str, list[tuple[str, bool]]] = {dim: [] for dim in DIMENSION_CYCLE}

    for row in rows:
        dim = _detect_dimension(row)
        status = str(row.get("status") or "").lower()
        # 中文注释：优先统计 active/verified 基因；如果状态缺失，则保守纳入总数。
        if status and status not in ACTIVE_STATUSES:
            continue
        fitness = _safe_float(row.get("fitness"), 0.0)
        verification = str(row.get("verification_status") or row.get("evidence_grade") or "").lower()
        elite = fitness >= ELITE_FITNESS_THRESHOLD or "elite" in verification or "pass" in verification
        metrics[dim]["total"] += 1
        metrics[dim]["active"] += 1 if status == "active" else 0
        metrics[dim]["elite"] += 1 if elite else 0
        dated[dim].append((str(row.get("created_at") or row.get("created") or ""), elite))

    for dim, data in metrics.items():
        total = int(data["total"])
        elite_count = int(data["elite"])
        data["elite_pct"] = round((elite_count / total * 100.0) if total else 0.0, 3)
        ordered = sorted(dated[dim], key=lambda pair: pair[0])
        if len(ordered) >= 4:
            mid = len(ordered) // 2
            older = ordered[:mid]
            recent = ordered[mid:]
            data["older_elite_pct"] = round(sum(1 for _, ok in older if ok) / len(older) * 100.0, 3)
            data["recent_elite_pct"] = round(sum(1 for _, ok in recent if ok) / len(recent) * 100.0, 3)
    return metrics


def _trend_for(metric: dict[str, Any]) -> str:
    recent = metric.get("recent_elite_pct")
    older = metric.get("older_elite_pct")
    if recent is None or older is None:
        return "insufficient_data"
    delta = float(recent) - float(older)
    if delta >= 3.0:
        return "rising"
    if delta <= -3.0:
        return "falling"
    return "stable"


def run_picoapex_gate() -> bool:
    """运行 PicoAPEX 饱和度门禁，打印 JSON，返回是否成功完成本地计算。"""
    rows, error = _read_gene_rows(DEFAULT_GENE_DB)
    metrics = _compute_metrics(rows)
    state = _load_json_file(DEFAULT_STATE_PATH)
    current = _current_dimension(state, metrics)
    current_metric = metrics.get(current, {"total": 0, "elite": 0, "elite_pct": 0.0})
    elite_pct = float(current_metric.get("elite_pct") or 0.0)
    saturation_pct = elite_pct
    saturated = saturation_pct >= SATURATION_THRESHOLD_PCT
    next_dim = _next_dimension(current)

    recommendations: list[str] = []
    if error:
        recommendations.append("gene_db_unavailable: inspect local GeneDB path before switching dimensions")
    elif saturated:
        recommendations.append(f"saturation >= 98%; recommend automatic switch to next_dimension={next_dim}")
    else:
        recommendations.append(f"continue current_dimension={current}; saturation below 98%")
    low_sample_dims = [dim for dim, data in metrics.items() if int(data.get("total", 0)) == 0]
    if low_sample_dims:
        recommendations.append("dimensions_without_active_verified_genes=" + ",".join(low_sample_dims))

    payload = {
        "schema": SCHEMA,
        "status": "error" if error else ("saturated" if saturated else "monitoring"),
        "current_dimension": current,
        "saturation_pct": round(saturation_pct, 3),
        "elite_pct": round(elite_pct, 3),
        "trend": _trend_for(current_metric),
        "next_dimension": next_dim,
        "recommendations": recommendations,
        "boundary": BOUNDARY,
        # 中文注释：附加本地细节不改变主 schema，便于门禁审计。
        "computed_at": _now(),
        "threshold_pct": SATURATION_THRESHOLD_PCT,
        "elite_fitness_threshold": ELITE_FITNESS_THRESHOLD,
        "dimension_cycle": DIMENSION_CYCLE,
        "dimension_metrics": metrics,
        "gene_db": str(DEFAULT_GENE_DB),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return error is None


if __name__ == "__main__":
    raise SystemExit(0 if run_picoapex_gate() else 1)
