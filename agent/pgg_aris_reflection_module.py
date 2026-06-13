#!/usr/bin/env python3
"""ARIS 三层深度反思模块。

边界：internal PGG gate; local computation only; no LLM/network; no AGI/T5/ASI claim。
本模块仅读取本地 PGG 基因库/状态文件，执行确定性统计与模式匹配。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

DEFAULT_GENE_DB = Path(
    os.environ.get(
        "PGG_GENE_DB",
        "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3",
    )
)
SCHEMA = "pgg.aris.reflection_module.v1"
BOUNDARY = "internal PGG gate; local computation only; no LLM/network; no AGI/T5/ASI claim"
DIMENSIONS = ["cognition", "reasoning", "planning", "coding", "analysis"]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def _json_maybe(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return fallback
    try:
        return json.loads(str(value))
    except Exception:
        return fallback


def _select_rows(db_path: Path) -> tuple[list[dict[str, Any]], str | None]:
    """中文注释：一次性读取本地 evolution_genes，后续三层反思均基于该快照。"""
    if not db_path.exists():
        return [], f"GeneDB not found: {db_path}"
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        try:
            cols = [str(r[1]) for r in con.execute("PRAGMA table_info(evolution_genes)").fetchall()]
            if not cols:
                return [], "evolution_genes table missing"
            select_cols = ", ".join(f'"{c}"' for c in cols)
            rows = con.execute(f"SELECT {select_cols} FROM evolution_genes").fetchall()
            return [dict(row) for row in rows], None
        finally:
            con.close()
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def _detect_dimension(row: dict[str, Any]) -> str:
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
    table = {
        "coding": ("coding", "code", "python", "pytest", "module", "script", "cli", "代码", "编程", "测试"),
        "planning": ("planning", "plan", "scheduler", "cron", "workflow", "pipeline", "计划", "规划", "调度"),
        "reasoning": ("reasoning", "logic", "proof", "verify", "gate", "推理", "逻辑", "证明", "核验"),
        "analysis": ("analysis", "audit", "metric", "benchmark", "reflection", "observe", "分析", "审计", "指标", "反思"),
        "cognition": ("cognition", "memory", "knowledge", "learn", "gene", "skill", "认知", "记忆", "知识", "学习", "基因"),
    }
    for dim in ("reasoning", "planning", "coding", "analysis", "cognition"):
        if any(token in text for token in table[dim]):
            return dim
    return "cognition"


def _source_gate_consistency(row: dict[str, Any]) -> tuple[bool, str]:
    """L1：检查 source → gate 是否有基本一致性。"""
    source_raw = row.get("source_refs_json") or row.get("source") or row.get("absorbed_knowledge")
    source = _json_maybe(source_raw, source_raw)
    source_text = _as_text(source).lower()
    gate = str(row.get("gate_type") or "").lower()
    boundary = str(row.get("boundary") or "").lower()

    if not source_text.strip():
        return False, "missing_source"
    if not gate.strip():
        return False, "missing_gate"

    # 中文注释：source 中出现的高风险能力，gate/boundary 应有对应门禁或边界词。
    checks = {
        "network": ("network", "http", "api", "联网", "网络"),
        "llm": ("llm", "model", "openai", "claude", "gpt", "模型"),
        "write": ("write", "chmod", "delete", "rm ", "写入", "删除"),
        "github": ("github", "pull request", "repo", "仓库"),
    }
    gate_text = gate + " " + boundary
    for label, tokens in checks.items():
        if any(token in source_text for token in tokens) and label not in gate_text and "local" not in gate_text:
            return False, f"source_mentions_{label}_without_gate_marker"
    return True, "consistent"


def _l1_fact_check(rows: list[dict[str, Any]], db_error: str | None) -> dict[str, Any]:
    if db_error:
        return {
            "layer": "L1事实核验",
            "status": "fail",
            "findings": [db_error],
            "confidence": 0.2,
        }
    checked = 0
    mismatches: Counter[str] = Counter()
    for row in rows:
        checked += 1
        ok, reason = _source_gate_consistency(row)
        if not ok:
            mismatches[reason] += 1
    mismatch_total = sum(mismatches.values())
    ratio = mismatch_total / checked if checked else 1.0
    status = "pass" if checked and ratio <= 0.10 else "warn" if checked and ratio <= 0.30 else "fail"
    findings = [
        f"checked_genes={checked}",
        f"source_gate_mismatch={mismatch_total}",
        "top_mismatch_patterns=" + json.dumps(mismatches.most_common(5), ensure_ascii=False),
    ]
    return {
        "layer": "L1事实核验",
        "status": status,
        "findings": findings,
        "confidence": round(max(0.25, 1.0 - ratio), 3),
    }


def _l2_failure_pattern(rows: list[dict[str, Any]], db_error: str | None) -> dict[str, Any]:
    """L2：分析 rejected/candidate/pending 等 failure pattern。"""
    if db_error:
        return {"layer": "L2逻辑归因", "status": "fail", "findings": [db_error], "confidence": 0.2}
    failures: Counter[str] = Counter()
    status_dist: Counter[str] = Counter(str(r.get("status") or "unknown") for r in rows)
    for row in rows:
        status = str(row.get("status") or "").lower()
        verification = str(row.get("verification_status") or "").lower()
        text = " ".join(_as_text(row.get(k)).lower() for k in ("absorbed_knowledge", "repair_mechanism", "boundary", "reusable_rule"))
        if status in {"rejected", "retired"} or "fail" in verification or "pending" in verification:
            if "missing" in text or "缺失" in text:
                failures["missing_precondition_or_evidence"] += 1
            elif "boundary" in text or "边界" in text or "no llm" in text or "network" in text:
                failures["boundary_constraint_conflict"] += 1
            elif "duplicate" in text or "重复" in text:
                failures["duplicate_or_redundant_gene"] += 1
            elif "source" in text or "evidence" in text or "证据" in text:
                failures["weak_source_evidence"] += 1
            else:
                failures["unclassified_failure"] += 1
    failure_total = sum(failures.values())
    total = len(rows)
    failure_ratio = failure_total / total if total else 1.0
    status = "pass" if failure_ratio <= 0.25 else "warn" if failure_ratio <= 0.55 else "fail"
    findings = [
        "status_distribution=" + json.dumps(status_dist.most_common(), ensure_ascii=False),
        "failure_patterns=" + json.dumps(failures.most_common(8), ensure_ascii=False),
        f"failure_ratio={failure_ratio:.3f}",
    ]
    return {
        "layer": "L2逻辑归因",
        "status": status,
        "findings": findings,
        "confidence": round(max(0.25, min(0.95, 1.0 - failure_ratio / 2.0)), 3),
    }


def _token_patterns(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", text.lower()))
    stop = {"the", "and", "with", "from", "local", "only", "status", "gene", "基因", "本地"}
    return {t for t in tokens if t not in stop}


def _l3_cross_domain(rows: list[dict[str, Any]], db_error: str | None) -> dict[str, Any]:
    """L3：跨 skill/domain 做模式匹配，寻找可复用/共振模式。"""
    if db_error:
        return {"layer": "L3跨域共振", "status": "fail", "findings": [db_error], "confidence": 0.2}
    by_dim: dict[str, Counter[str]] = defaultdict(Counter)
    dim_count: Counter[str] = Counter()
    for row in rows:
        dim = _detect_dimension(row)
        dim_count[dim] += 1
        text = " ".join(_as_text(row.get(k)) for k in ("gate_type", "gene_name", "repair_mechanism", "reusable_rule", "absorbed_knowledge"))
        by_dim[dim].update(_token_patterns(text))

    resonance: list[tuple[str, list[str]]] = []
    all_patterns = set().union(*(counter.keys() for counter in by_dim.values())) if by_dim else set()
    for pattern in sorted(all_patterns):
        dims = [dim for dim in DIMENSIONS if by_dim[dim].get(pattern, 0) >= 2]
        if len(dims) >= 2:
            resonance.append((pattern, dims))
    resonance = resonance[:10]
    covered_dims = sum(1 for dim in DIMENSIONS if dim_count[dim] > 0)
    status = "pass" if resonance and covered_dims >= 3 else "warn" if covered_dims >= 2 else "fail"
    findings = [
        "dimension_distribution=" + json.dumps(dim_count.most_common(), ensure_ascii=False),
        "cross_domain_patterns=" + json.dumps(resonance, ensure_ascii=False),
        f"covered_dimensions={covered_dims}/5",
    ]
    confidence = 0.35 + min(0.4, len(resonance) * 0.04) + min(0.2, covered_dims * 0.04)
    return {
        "layer": "L3跨域共振",
        "status": status,
        "findings": findings,
        "confidence": round(min(0.95, confidence), 3),
    }


def _score(layers: Iterable[dict[str, Any]]) -> float:
    status_weight = {"pass": 1.0, "warn": 0.65, "fail": 0.25}
    vals = []
    for layer in layers:
        vals.append(status_weight.get(str(layer.get("status")), 0.4) * float(layer.get("confidence") or 0.0))
    return round(sum(vals) / len(vals) * 100.0, 2) if vals else 0.0


def run_aris_reflection() -> bool:
    """运行 ARIS 三层反思，打印指定 JSON，返回本地计算是否完成。"""
    rows, db_error = _select_rows(DEFAULT_GENE_DB)
    layers = [
        _l1_fact_check(rows, db_error),
        _l2_failure_pattern(rows, db_error),
        _l3_cross_domain(rows, db_error),
    ]
    score = _score(layers)
    worst = "fail" if any(l["status"] == "fail" for l in layers) else "warn" if any(l["status"] == "warn" for l in layers) else "pass"
    summary = f"ARIS三层反思完成：overall={worst}, score={score}, genes={len(rows)}"
    payload = {
        "schema": SCHEMA,
        "layers": layers,
        "summary": summary,
        "score": score,
        "boundary": BOUNDARY,
        # 中文注释：附加时间戳与本地数据源，便于审计复现。
        "computed_at": _now(),
        "gene_db": str(DEFAULT_GENE_DB),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return db_error is None


if __name__ == "__main__":
    raise SystemExit(0 if run_aris_reflection() else 1)
