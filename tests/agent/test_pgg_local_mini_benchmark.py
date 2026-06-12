"""Tests for PGG Archon 本地确定性 mini-benchmark。

测试覆盖:
  - run_mini_benchmark() 总体输出结构
  - validate_standard_gene() 的 PASS/BLOCK 路径
  - fuse_standard_genes() 的 additive/multiplicative 路径
  - GeneDB schema 查询
  - scan_source 扫描
  - 安全边界声明
"""

from __future__ import annotations

from agent.pgg_local_mini_benchmark import (
    STANDARD_GENE,
    SAMPLE_GENE_SOURCE,
    check_genedb_schema,
    fuse_standard_genes,
    run_mini_benchmark,
    scan_source,
    validate_standard_gene,
)


class TestRunMiniBenchmark:
    """run_mini_benchmark() 总体输出测试。"""

    def test_returns_correct_schema(self) -> None:
        result = run_mini_benchmark()
        assert result["schema"] == "PGGMiniBenchmark/v1"

    def test_returns_pass_or_watch(self) -> None:
        result = run_mini_benchmark()
        assert result["status"] in ("PASS", "WATCH")

    def test_score_is_integers(self) -> None:
        result = run_mini_benchmark()
        assert isinstance(result["pass_count"], int)
        assert isinstance(result["total_count"], int)
        assert result["pass_count"] >= 0
        assert result["total_count"] > 0
        assert result["pass_count"] <= result["total_count"]

    def test_has_five_results(self) -> None:
        result = run_mini_benchmark()
        assert len(result["results"]) == 5

    def test_each_result_has_name_status_score(self) -> None:
        result = run_mini_benchmark()
        for r in result["results"]:
            assert "name" in r
            assert "status" in r
            assert r["status"] in ("PASS", "FAIL")
            assert "pass_count" in r
            assert "total" in r

    def test_boundary_declaration(self) -> None:
        result = run_mini_benchmark()
        assert "local deterministic mini-benchmark" in result["boundary"]
        assert "not external/community benchmark" in result["boundary"]
        assert "not AGI level proof" in result["boundary"]


class TestValidateStandardGene:
    """validate_standard_gene() 测试。"""

    def test_valid_gene_passes(self) -> None:
        result = validate_standard_gene(STANDARD_GENE)
        assert result["valid"] is True
        assert result["reason"] == "PASS"

    def test_missing_fields_blocked(self) -> None:
        broken: dict = {"gene_id": "broken"}
        result = validate_standard_gene(broken)
        assert result["valid"] is False
        assert "BLOCK" in result["reason"]

    def test_non_dict_blocked(self) -> None:
        result = validate_standard_gene("not_a_dict")
        assert result["valid"] is False
        assert "BLOCK" in result["reason"] or "not a dict" in result["reason"]

    def test_type_mismatch_blocked(self) -> None:
        wrong_type: dict = dict(STANDARD_GENE)
        wrong_type["fitness"] = "not_an_int"  # should be int
        result = validate_standard_gene(wrong_type)
        assert result["valid"] is False


class TestFuseStandardGenes:
    """fuse_standard_genes() 测试。"""

    def test_additive_two_equal_fitness(self) -> None:
        gene_a = dict(STANDARD_GENE)
        gene_b = dict(STANDARD_GENE)
        gene_b["gene_id"] = "gene_002"
        result = fuse_standard_genes(gene_a, gene_b, mode="additive")
        assert result["status"] == "PASS"
        assert result["fused_fitness"] == 1600  # 800 + 800
        assert result["synergy"] > 0.0

    def test_multiplicative_different_fitness(self) -> None:
        gene_a = dict(STANDARD_GENE)  # fitness=800
        gene_b = dict(STANDARD_GENE)
        gene_b["gene_id"] = "gene_003"
        gene_b["fitness"] = 600
        result = fuse_standard_genes(gene_a, gene_b, mode="multiplicative")
        expected = int((800 * 600) ** 0.5)  # ≈ 692
        assert result["status"] == "PASS"
        assert result["fused_fitness"] == expected

    def test_broken_gene_blocked(self) -> None:
        gene_a = {"gene_id": "broken"}
        gene_b = dict(STANDARD_GENE)
        result = fuse_standard_genes(gene_a, gene_b)
        assert result["status"] == "BLOCK"

    def test_fusion_returns_synergy(self) -> None:
        gene_a = dict(STANDARD_GENE)
        gene_b = dict(STANDARD_GENE)
        gene_b["gene_id"] = "gene_004"
        result = fuse_standard_genes(gene_a, gene_b)
        assert "synergy" in result
        assert isinstance(result["synergy"], float)

    def test_fusion_mode_default_additive(self) -> None:
        gene_a = dict(STANDARD_GENE)
        gene_b = dict(STANDARD_GENE)
        gene_b["gene_id"] = "gene_005"
        result = fuse_standard_genes(gene_a, gene_b)
        assert result["mode"] == "additive"
        assert result["fused_fitness"] == 1600


class TestGeneDBSchema:
    """GeneDB schema 查询测试。"""

    def test_all_required_columns_found(self) -> None:
        result = check_genedb_schema()
        assert result["ok"] is True
        assert len(result["missing"]) == 0

    def test_fitness_found(self) -> None:
        result = check_genedb_schema()
        assert "fitness" in result["columns_found"]

    def test_execution_count_found(self) -> None:
        result = check_genedb_schema()
        assert "execution_count" in result["columns_found"]

    def test_last_executed_found(self) -> None:
        result = check_genedb_schema()
        assert "last_executed" in result["columns_found"]

    def test_total_columns_greater_than_required(self) -> None:
        result = check_genedb_schema()
        assert len(result["all_columns"]) >= 21


class TestScanSource:
    """scan_source() 测试。"""

    def test_scans_py_source_finds_genes(self) -> None:
        result = scan_source(
            filepath="test_sample.py",
            source_code=SAMPLE_GENE_SOURCE,
        )
        assert result["status"] == "PASS"
        assert result["count"] == 2

    def test_returns_gene_ids(self) -> None:
        result = scan_source(
            filepath="test_sample.py",
            source_code=SAMPLE_GENE_SOURCE,
        )
        gene_ids = [g.get("gene_id", "") for g in result["genes_found"]]
        assert "gene_scan_001" in gene_ids
        assert "gene_scan_002" in gene_ids

    def test_empty_source_returns_block(self) -> None:
        result = scan_source(
            filepath="empty.py",
            source_code="# just a comment\nx = 1\n",
        )
        assert result["status"] == "BLOCK"
        assert result["count"] == 0

    def test_no_source_code_provided(self) -> None:
        result = scan_source(filepath="no_source.py")
        assert result["status"] == "BLOCK"
        assert "not provided" in result.get("reason", "")

    def test_source_with_no_gene_blocks(self) -> None:
        result = scan_source(
            filepath="no_gene.py",
            source_code="x = 1\ny = 'hello'\n",
        )
        assert result["status"] == "BLOCK"
        assert result["count"] == 0


class TestSafetyBoundaries:
    """安全边界测试。"""

    def test_no_llm_call_in_benchmark(self) -> None:
        """确认 benchmark 模块不导入 LLM 相关模块。"""
        import agent.pgg_local_mini_benchmark as bm

        # 检查模块源码不含 LLM/网络调用
        import inspect
        source = inspect.getsource(bm)
        # LLM/openai/anthropic 等关键字不应出现在源码中
        forbidden = ["openai", "anthropic", "requests.get", "urllib", "httpx"]
        for kw in forbidden:
            assert kw not in source, f"benchmark should not import/use {kw}"

    def test_boundary_string_present(self) -> None:
        """确认 benchmark 输出包含边界声明。"""
        from agent.pgg_local_mini_benchmark import BOUNDARY
        assert "local deterministic" in BOUNDARY
        assert "not external/community benchmark" in BOUNDARY
        assert "not AGI level proof" in BOUNDARY
