"""PGG Archon 本地确定性 mini-benchmark。

测试基因融合引擎的基本功能。纯本地、确定性、不调用 LLM/网络。

安全边界:
  - 不调用 LLM
  - 无网络
  - 不修改 Hermes core/provider/scheduler
  - 不声称外部 benchmark 通过
"""

from __future__ import annotations

import ast
import re
from typing import Any

# ---------------------------------------------------------------------------
# Schema / output constants
# ---------------------------------------------------------------------------
SCHEMA = "PGGMiniBenchmark/v1"
BOUNDARY = (
    "local deterministic mini-benchmark; "
    "not external/community benchmark; "
    "not AGI level proof"
)

# ---------------------------------------------------------------------------
# 标准基因结构 (模拟 GeneDB 中的基因记录)
# ---------------------------------------------------------------------------
STANDARD_GENE_SCHEMA: dict[str, type] = {
    "gene_id": str,
    "gene_name": str,
    "fitness": int,
    "status": str,
    "gate_type": str,
    "severity_rank": int,
    "execution_count": int,
    "last_executed": str,
}

STANDARD_GENE: dict[str, Any] = {
    "gene_id": "gene_001",
    "gene_name": "test_gene",
    "fitness": 800,
    "status": "active",
    "gate_type": "recommend",
    "severity_rank": 3,
    "execution_count": 42,
    "last_executed": "2026-06-11T12:00:00",
}

GENEDB_SCHEMA_COLUMNS: list[str] = [
    "gene_id", "cycle_id", "created_at", "defect_no", "defect_name",
    "gene_name", "absorbed_knowledge", "source_refs_json", "repair_mechanism",
    "severity_rank", "apex_variables", "gate_type", "reusable_rule",
    "status", "evidence_grade", "verification_status", "boundary",
    "gene_hash", "fitness", "last_executed", "execution_count",
]

REQUIRED_GENEDB_COLUMNS: list[str] = [
    "fitness", "execution_count", "last_executed",
]

# ---------------------------------------------------------------------------
# 基因验证 (validate_standard_gene)
# ---------------------------------------------------------------------------


def validate_standard_gene(gene: Any) -> dict[str, Any]:
    """验证单个基因结构是否符合标准 schema。

    Args:
        gene: 任意输入，期望为 dict。

    Returns:
        {"gene": ..., "valid": True|False, "reason": ...}
    """
    if not isinstance(gene, dict):
        return {"gene": gene, "valid": False, "reason": "input is not a dict"}

    missing: list[str] = []
    type_mismatch: list[str] = []

    for field, expected_type in STANDARD_GENE_SCHEMA.items():
        if field not in gene:
            missing.append(field)
        elif not isinstance(gene[field], expected_type):
            type_mismatch.append(
                f"{field}: expected {expected_type.__name__}, "
                f"got {type(gene[field]).__name__}"
            )

    errors: list[str] = []
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if type_mismatch:
        errors.append(f"type mismatch: {'; '.join(type_mismatch)}")

    if not errors:
        return {"gene": gene, "valid": True, "reason": "PASS"}
    return {"gene": gene, "valid": False, "reason": "BLOCK; " + "; ".join(errors)}


# ---------------------------------------------------------------------------
# 基因融合 (fuse_standard_genes)
# ---------------------------------------------------------------------------


def _synergy_score(gene_a: dict[str, Any], gene_b: dict[str, Any]) -> float:
    """计算两个基因的协同得分 (0.0 ~ 1.0)。"""
    fitness_a = gene_a.get("fitness", 0)
    fitness_b = gene_b.get("fitness", 0)
    if fitness_a <= 0 or fitness_b <= 0:
        return 0.0
    # 协同 = 几何平均 / 1000，归一化到 0~1
    synergy = (fitness_a * fitness_b) ** 0.5 / 1000.0
    return min(synergy, 1.0)


def fuse_standard_genes(
    gene_a: dict[str, Any],
    gene_b: dict[str, Any],
    mode: str = "additive",
) -> dict[str, Any]:
    """融合两个基因，返回融合结果。

    Args:
        gene_a: 第一个基因 dict。
        gene_b: 第二个基因 dict。
        mode: "additive" 或 "multiplicative"。

    Returns:
        {
            "gene_a": ..., "gene_b": ...,
            "fused_fitness": int,
            "synergy": float,
            "mode": str,
            "status": "PASS" | "BLOCK",
            "reason": str,
        }
    """
    # 先验证两个基因
    va = validate_standard_gene(gene_a)
    vb = validate_standard_gene(gene_b)

    if not va["valid"]:
        return {
            "gene_a": gene_a,
            "gene_b": gene_b,
            "fused_fitness": 0,
            "synergy": 0.0,
            "mode": mode,
            "status": "BLOCK",
            "reason": f"gene_a validation failed: {va['reason']}",
        }
    if not vb["valid"]:
        return {
            "gene_a": gene_a,
            "gene_b": gene_b,
            "fused_fitness": 0,
            "synergy": 0.0,
            "mode": mode,
            "status": "BLOCK",
            "reason": f"gene_b validation failed: {vb['reason']}",
        }

    fitness_a = gene_a.get("fitness", 0)
    fitness_b = gene_b.get("fitness", 0)
    synergy = _synergy_score(gene_a, gene_b)

    if mode == "multiplicative":
        fused_fitness = int((fitness_a * fitness_b) ** 0.5)
    else:
        # additive
        fused_fitness = fitness_a + fitness_b

    return {
        "gene_a": gene_a,
        "gene_b": gene_b,
        "fused_fitness": fused_fitness,
        "synergy": round(synergy, 4),
        "mode": mode,
        "status": "PASS",
        "reason": f"fused fitness={fused_fitness}, synergy={synergy:.4f}",
    }


# ---------------------------------------------------------------------------
# GeneDB schema query
# ---------------------------------------------------------------------------


def check_genedb_schema() -> dict[str, Any]:
    """确认 GeneDB schema 包含必需列。

    Returns:
        {"columns_found": [...], "missing": [...], "ok": bool}
    """
    found: list[str] = []
    missing: list[str] = []

    for col in REQUIRED_GENEDB_COLUMNS:
        if col in GENEDB_SCHEMA_COLUMNS:
            found.append(col)
        else:
            missing.append(col)

    return {
        "columns_found": found,
        "all_columns": GENEDB_SCHEMA_COLUMNS,
        "missing": missing,
        "ok": len(missing) == 0,
    }


# ---------------------------------------------------------------------------
# scan_source — 扫描 .py 文件返回基因列表
# ---------------------------------------------------------------------------


def _extract_genes_from_source(code: str) -> list[dict[str, Any]]:
    """从 Python 源码中提取基因定义。

    检测所有顶层 dict 变量定义，筛选包含 "gene_id" 或 "gene_name" 字段的 dict。
    """
    genes: list[dict[str, Any]] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return genes

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(
                    node.value, ast.Dict
                ):
                    # 尝试提取 dict keys 判断是否基因
                    keys = [
                        k.value  # type: ignore[attr-defined]
                        for k in node.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                    ]
                    if "gene_id" in keys or "gene_name" in keys:
                        gene: dict[str, Any] = {}
                        for k, v in zip(node.value.keys, node.value.values):
                            if isinstance(k, ast.Constant) and isinstance(
                                k.value, str
                            ):
                                if isinstance(v, ast.Constant):
                                    gene[k.value] = v.value
                                elif isinstance(v, ast.List):
                                    gene[k.value] = [
                                        e.value
                                        for e in v.elts
                                        if isinstance(e, ast.Constant)
                                    ]
                                elif isinstance(v, ast.Dict):
                                    gene[k.value] = {}
                        if gene:
                            genes.append(gene)

    return genes


def scan_source(filepath: str, source_code: str | None = None) -> dict[str, Any]:
    """扫描一个 .py 文件源码，返回提取的基因列表。

    Args:
        filepath: 文件路径（用于标识）。
        source_code: 源码字符串。若不提供则尝试从文件读取。

    Returns:
        {"filepath": ..., "genes_found": [...], "count": int, "status": "PASS"|"BLOCK"}
    """
    if source_code is None:
        return {
            "filepath": filepath,
            "genes_found": [],
            "count": 0,
            "status": "BLOCK",
            "reason": "source_code not provided",
        }

    genes = _extract_genes_from_source(source_code)

    return {
        "filepath": filepath,
        "genes_found": genes,
        "count": len(genes),
        "status": "PASS" if genes else "BLOCK",
        "reason": f"found {len(genes)} gene(s)" if genes else "no genes found in source",
    }


# ---------------------------------------------------------------------------
# 主 benchmark 运行器
# ---------------------------------------------------------------------------

# 供 scan_source 测试用的示例源码
SAMPLE_GENE_SOURCE = """
# 测试基因定义
test_gene_1 = {
    "gene_id": "gene_scan_001",
    "gene_name": "scan_test_gene",
    "fitness": 750,
    "status": "active",
}

another_var = 42

test_gene_2 = {
    "gene_id": "gene_scan_002",
    "gene_name": "scan_test_gene_2",
    "fitness": 600,
    "status": "candidate",
}
"""


def _test_validate_standard_gene() -> dict[str, Any]:
    """测试 a) validate_standard_gene: 标准基因 PASS, 残缺 BLOCK。"""
    # 1) 标准基因 → PASS
    result_ok = validate_standard_gene(STANDARD_GENE)
    ok_pass = result_ok["valid"]

    # 2) 残缺基因 → BLOCK
    broken_gene: dict[str, Any] = {
        "gene_id": "broken",
        # 缺少 gene_name, fitness, status, gate_type 等
    }
    result_broken = validate_standard_gene(broken_gene)
    broken_block = not result_broken["valid"]

    # 3) 非 dict → BLOCK
    result_nondict = validate_standard_gene("not_a_dict")
    nondict_block = not result_nondict["valid"]

    passed = ok_pass and broken_block and nondict_block
    total = 3
    pass_count = sum([ok_pass, broken_block, nondict_block])

    return {
        "name": "validate_standard_gene",
        "pass_count": pass_count,
        "total": total,
        "status": "PASS" if passed else "FAIL",
        "details": {
            "standard_gene_pass": ok_pass,
            "broken_gene_block": broken_block,
            "nondict_block": nondict_block,
        },
    }


def _test_fuse_standard_genes() -> dict[str, Any]:
    """测试 b) fuse_standard_genes: 2个 fitness=800 基因 → PASS + synergy>0。"""
    gene_a = dict(STANDARD_GENE)
    gene_b = dict(STANDARD_GENE)
    gene_b["gene_id"] = "gene_002"

    result = fuse_standard_genes(gene_a, gene_b, mode="additive")

    passed = (
        result["status"] == "PASS"
        and result["fused_fitness"] == 1600
        and result["synergy"] > 0.0
    )

    return {
        "name": "fuse_standard_genes_additive",
        "pass_count": 1 if passed else 0,
        "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {
            "fused_fitness": result["fused_fitness"],
            "synergy": result["synergy"],
            "status": result["status"],
        },
    }


def _test_fuse_standard_genes_multiplicative() -> dict[str, Any]:
    """测试 c) fuse_standard_genes (multiplicative): 不同 fitness → PASS。"""
    gene_a = dict(STANDARD_GENE)  # fitness=800
    gene_b = dict(STANDARD_GENE)
    gene_b["gene_id"] = "gene_003"
    gene_b["fitness"] = 600

    result = fuse_standard_genes(gene_a, gene_b, mode="multiplicative")

    expected_fitness = int((800 * 600) ** 0.5)  # ≈ 692
    passed = result["status"] == "PASS" and result["fused_fitness"] == expected_fitness

    return {
        "name": "fuse_standard_genes_multiplicative",
        "pass_count": 1 if passed else 0,
        "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {
            "fused_fitness": result["fused_fitness"],
            "expected_fitness": expected_fitness,
            "synergy": result["synergy"],
            "status": result["status"],
        },
    }


def _test_genedb_schema() -> dict[str, Any]:
    """测试 d) GeneDB schema: 确认 fitness/execution_count/last_executed 存在。"""
    result = check_genedb_schema()

    passed = result["ok"] and len(result["missing"]) == 0

    return {
        "name": "genedb_schema_query",
        "pass_count": 1 if passed else 0,
        "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {
            "columns_found": result["columns_found"],
            "missing": result["missing"],
            "total_columns": len(result["all_columns"]),
        },
    }


def _test_scan_source() -> dict[str, Any]:
    """测试 e) scan_source: 扫描 .py 源码 → 返回基因列表。"""
    result = scan_source(
        filepath="test_sample_source.py",
        source_code=SAMPLE_GENE_SOURCE,
    )

    # 应找到 2 个基因
    passed = result["status"] == "PASS" and result["count"] == 2

    return {
        "name": "scan_source",
        "pass_count": 1 if passed else 0,
        "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {
            "genes_found_count": result["count"],
            "gene_ids": [g.get("gene_id", "") for g in result["genes_found"]],
            "status": result["status"],
        },
    }


def run_mini_benchmark() -> dict[str, Any]:
    """运行所有 mini-benchmark 测试。

    Returns:
        {
            "schema": "PGGMiniBenchmark/v1",
            "status": "PASS" | "WATCH",
            "pass_count": int,
            "total_count": int,
            "results": [...],
            "boundary": "...",
        }
    """
    tests = [
        _test_validate_standard_gene(),
        _test_fuse_standard_genes(),
        _test_fuse_standard_genes_multiplicative(),
        _test_genedb_schema(),
        _test_scan_source(),
    ]

    total_count = sum(t["total"] for t in tests)
    pass_count = sum(t["pass_count"] for t in tests)

    # 只要没有 FAIL 就 PASS，有 FAIL 但部分通过就 WATCH
    all_fail = all(t["status"] == "FAIL" for t in tests)
    if all_fail:
        overall = "FAIL"
    elif pass_count == total_count:
        overall = "PASS"
    else:
        overall = "WATCH"

    return {
        "schema": SCHEMA,
        "status": overall,
        "pass_count": pass_count,
        "total_count": total_count,
        "results": tests,
        "boundary": BOUNDARY,
    }


if __name__ == "__main__":
    import json
    result = run_mini_benchmark()
    print(json.dumps(result, indent=2, ensure_ascii=False))
