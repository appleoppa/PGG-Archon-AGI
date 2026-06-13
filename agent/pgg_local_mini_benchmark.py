"""
PGG Local Mini Benchmark — Python bridge
Core logic (validate / fuse / synergy / genedb-schema / run-all) backed by
hermes_pgg_mini_benchmark native .so when available, pure-Python fallback.

Boundary:
  - local deterministic; no LLM calls, no network
  - not external/community benchmark
  - not AGI level proof
"""
from __future__ import annotations

import json
import sys
from typing import Any

try:
    import hermes_pgg_mini_benchmark as _native
    _NATIVE = True
except ImportError:
    _NATIVE = False

SCHEMA = "PGGMiniBenchmark/v1"
BOUNDARY = (
    "local deterministic mini-benchmark; "
    "not external/community benchmark; "
    "not AGI level proof"
)

BENCHMARK_GENE_SCHEMA: dict[str, type] = {
    "gene_id": str,
    "gene_name": str,
    "fitness": int,
    "status": str,
    "gate_type": str,
    "severity_rank": int,
    "execution_count": int,
    "last_executed": str,
}

BENCHMARK_GENE: dict[str, Any] = {
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
# Gene validation (fallback pure-Python)
# ---------------------------------------------------------------------------

def validate_benchmark_gene(gene: Any) -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.validate_benchmark_gene(json.dumps(gene)))
    # Python fallback
    if not isinstance(gene, dict):
        return {"gene": gene, "valid": False, "reason": "input is not a dict"}
    missing: list[str] = []
    type_mismatch: list[str] = []
    for field, expected_type in BENCHMARK_GENE_SCHEMA.items():
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
# Synergy score
# ---------------------------------------------------------------------------

def _synergy_score(gene_a: dict[str, Any], gene_b: dict[str, Any]) -> float:
    fitness_a = gene_a.get("fitness", 0)
    fitness_b = gene_b.get("fitness", 0)
    if fitness_a <= 0 or fitness_b <= 0:
        return 0.0
    synergy = (fitness_a * fitness_b) ** 0.5 / 1000.0
    return min(synergy, 1.0)

# ---------------------------------------------------------------------------
# Gene fusion
# ---------------------------------------------------------------------------

def fuse_benchmark_genes(
    gene_a: dict[str, Any],
    gene_b: dict[str, Any],
    mode: str = "additive",
) -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.fuse_benchmark_genes(
            json.dumps(gene_a), json.dumps(gene_b), mode
        ))
    # Python fallback
    va = validate_benchmark_gene(gene_a)
    vb = validate_benchmark_gene(gene_b)
    if not va["valid"]:
        return {"gene_a": gene_a, "gene_b": gene_b, "fused_fitness": 0,
                "synergy": 0.0, "mode": mode, "status": "BLOCK",
                "reason": f"gene_a validation failed: {va['reason']}"}
    if not vb["valid"]:
        return {"gene_a": gene_a, "gene_b": gene_b, "fused_fitness": 0,
                "synergy": 0.0, "mode": mode, "status": "BLOCK",
                "reason": f"gene_b validation failed: {vb['reason']}"}
    fitness_a = gene_a.get("fitness", 0)
    fitness_b = gene_b.get("fitness", 0)
    synergy = _synergy_score(gene_a, gene_b)
    if mode == "multiplicative":
        fused_fitness = int((fitness_a * fitness_b) ** 0.5)
    else:
        fused_fitness = fitness_a + fitness_b
    return {
        "gene_a": gene_a, "gene_b": gene_b,
        "fused_fitness": fused_fitness, "synergy": round(synergy, 4),
        "mode": mode, "status": "PASS",
        "reason": f"fused fitness={fused_fitness}, synergy={synergy:.4f}",
    }

# ---------------------------------------------------------------------------
# GeneDB schema query
# ---------------------------------------------------------------------------

def check_genedb_schema() -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.check_genedb_schema())
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
# Test functions
# ---------------------------------------------------------------------------

def test_validate_standard_gene() -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.test_validate_standard_gene())
    result_ok = validate_benchmark_gene(BENCHMARK_GENE)
    ok_pass = result_ok["valid"]
    broken_gene: dict[str, Any] = {"gene_id": "broken"}
    result_broken = validate_benchmark_gene(broken_gene)
    broken_block = not result_broken["valid"]
    result_nondict = validate_benchmark_gene("not_a_dict")
    nondict_block = not result_nondict["valid"]
    passed = ok_pass and broken_block and nondict_block
    return {
        "name": "validate_standard_gene",
        "pass_count": sum([ok_pass, broken_block, nondict_block]),
        "total": 3,
        "status": "PASS" if passed else "FAIL",
        "details": {
            "standard_gene_pass": ok_pass,
            "broken_gene_block": broken_block,
            "nondict_block": nondict_block,
        },
    }

def test_fuse_standard_genes() -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.test_fuse_standard_genes())
    gene_a = dict(BENCHMARK_GENE)
    gene_b = dict(BENCHMARK_GENE)
    gene_b["gene_id"] = "gene_002"
    result = fuse_benchmark_genes(gene_a, gene_b, mode="additive")
    passed = result["status"] == "PASS" and result["fused_fitness"] == 1600 and result["synergy"] > 0.0
    return {
        "name": "fuse_standard_genes_additive",
        "pass_count": 1 if passed else 0, "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {"fused_fitness": result["fused_fitness"], "synergy": result["synergy"], "status": result["status"]},
    }

def test_fuse_standard_genes_multiplicative() -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.test_fuse_standard_genes_multiplicative())
    gene_a = dict(BENCHMARK_GENE)
    gene_b = dict(BENCHMARK_GENE)
    gene_b["gene_id"] = "gene_003"
    gene_b["fitness"] = 600
    result = fuse_benchmark_genes(gene_a, gene_b, mode="multiplicative")
    expected_fitness = int((800 * 600) ** 0.5)
    passed = result["status"] == "PASS" and result["fused_fitness"] == expected_fitness
    return {
        "name": "fuse_standard_genes_multiplicative",
        "pass_count": 1 if passed else 0, "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {"fused_fitness": result["fused_fitness"], "expected_fitness": expected_fitness,
                     "synergy": result["synergy"], "status": result["status"]},
    }

def test_genedb_schema() -> dict[str, Any]:
    if _NATIVE:
        return json.loads(_native.test_genedb_schema())
    result = check_genedb_schema()
    passed = result["ok"] and len(result["missing"]) == 0
    return {
        "name": "genedb_schema_query",
        "pass_count": 1 if passed else 0, "total": 1,
        "status": "PASS" if passed else "FAIL",
        "details": {"columns_found": result["columns_found"], "missing": result["missing"],
                     "total_columns": len(result["all_columns"])},
    }

# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_mini_benchmark() -> dict[str, Any]:
    """Run all mini-benchmark tests.

    Returns:
        {"schema": ..., "status": ..., "pass_count": ..., "total_count": ...,
         "results": [...], "boundary": ..., "native": ...}
    """
    if _NATIVE:
        return json.loads(_native.run_mini_benchmark())

    tests = [
        test_validate_standard_gene(),
        test_fuse_standard_genes(),
        test_fuse_standard_genes_multiplicative(),
        test_genedb_schema(),
    ]
    total_count = sum(t["total"] for t in tests)
    pass_count = sum(t["pass_count"] for t in tests)
    all_fail = all(t["status"] == "FAIL" for t in tests)
    overall = "FAIL" if all_fail else ("PASS" if pass_count == total_count else "WATCH")
    return {
        "schema": SCHEMA, "status": overall,
        "pass_count": pass_count, "total_count": total_count,
        "results": tests, "boundary": BOUNDARY,
        "native": "Python fallback",
    }

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_mini_benchmark()
    print(json.dumps(result, indent=2, ensure_ascii=False))