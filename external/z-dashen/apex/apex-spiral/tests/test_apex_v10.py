"""
APEX V10.2 测试用例
覆盖核心公式计算、Sigma统一标准、GraSP编译
"""

import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "py"))

import pytest
from apex_spiral.apex_v10 import (
    calculate_delta_g_v10,
    calculate_sigma_unified,
    calculate_grasp_compile,
    grasp_local_fix,
    __version__,
)
from apex_spiral.core import (
    ApexCalculator,
    ApexParams,
    LlmAgentParams,
    MasterParams,
    SelfRepairParams,
    CycleParams,
    HostHealthParams,
    calculate_delta_g,
)


# ============================================================
# V10 核心公式测试
# ============================================================

class TestCalculateDeltaGV10:
    """ΔG_v10 = (Λ_root × Θ × K × ξ × Ψ_host × Φ_cycle × Σ_unified) / (H × T × ε)"""

    def test_default_params(self):
        """默认参数下的基本计算"""
        result = calculate_delta_g_v10()
        assert isinstance(result, float)
        assert result >= 0.0

    def test_basic_calculation(self):
        """已知输入输出校验"""
        # Λ=0.95, Θ=0.5, K=1.0, ξ=1.0, Ψ=1.0, Φ=1.0, Σ=1.0
        # H=0.5, T=2.0, ε=1.0
        # numerator = 0.95 * 0.5 * 1.0 * 1.0 * 1.0 * 1.0 * 1.0 = 0.475
        # denominator = 0.5 * 2.0 * 1.0 = 1.0
        # result = 0.475
        result = calculate_delta_g_v10(
            lambda_root=0.95,
            theta=0.5,
            k_code=1.0,
            xi=1.0,
            psi_host=1.0,
            phi_cycle=1.0,
            sigma_unified=1.0,
            h=0.5,
            t=2.0,
            epsilon=1.0,
        )
        assert abs(result - 0.475) < 1e-6

    def test_zero_denominator_returns_zero(self):
        """H=0时返回0（防除零）"""
        result = calculate_delta_g_v10(h=0.0)
        assert result == 0.0

    def test_zero_t_returns_zero(self):
        """T=0时返回0（防除零）"""
        result = calculate_delta_g_v10(t=0.0)
        assert result == 0.0

    def test_large_sigma_increases_result(self):
        """Σ_unified增大时，ΔG应增大"""
        r1 = calculate_delta_g_v10(sigma_unified=1.0)
        r2 = calculate_delta_g_v10(sigma_unified=2.0)
        assert r2 > r1

    def test_small_h_increases_result(self):
        """H减小时，ΔG应增大（分母变小）"""
        r1 = calculate_delta_g_v10(h=0.5)
        r2 = calculate_delta_g_v10(h=0.1)
        assert r2 > r1

    def test_non_default_all_params(self):
        """全参数自定义"""
        result = calculate_delta_g_v10(
            lambda_root=0.9,
            theta=0.8,
            k_code=1.5,
            xi=1.2,
            psi_host=0.95,
            phi_cycle=1.1,
            sigma_unified=1.8,
            h=0.4,
            t=1.5,
            epsilon=1.1,
        )
        expected = (0.9 * 0.8 * 1.5 * 1.2 * 0.95 * 1.1 * 1.8) / (0.4 * 1.5 * 1.1)
        assert abs(result - expected) < 1e-6


# ============================================================
# Σ_unified 统一标准测试
# ============================================================

class TestSigmaUnified:
    """Σ_unified = schema × code × struct × native"""

    def test_all_ones(self):
        """全1.0时返回1.0"""
        result = calculate_sigma_unified()
        assert result == 1.0

    def test_basic_product(self):
        """基本乘积校验"""
        # Σ = 0.9 * 0.8 * 0.7 * 0.6 = 0.3024
        result = calculate_sigma_unified(0.9, 0.8, 0.7, 0.6)
        assert abs(result - 0.3024) < 1e-6

    def test_zero_any_factor_returns_zero(self):
        """任一因子为0则返回0"""
        assert calculate_sigma_unified(schema_compliance=0.0) == 0.0
        assert calculate_sigma_unified(code_standard=0.0) == 0.0
        assert calculate_sigma_unified(struct_standard=0.0) == 0.0
        assert calculate_sigma_unified(native_capability=0.0) == 0.0

    def test_perfect_standards(self):
        """完美标准（全1.0）"""
        result = calculate_sigma_unified(1.0, 1.0, 1.0, 1.0)
        assert result == 1.0

    def test_partial_standards(self):
        """部分达标场景"""
        result = calculate_sigma_unified(0.95, 0.90, 0.85, 0.80)
        expected = 0.95 * 0.90 * 0.85 * 0.80
        assert abs(result - expected) < 1e-6


# ============================================================
# GraSP 技能编译测试
# ============================================================

class TestGraSPCompile:
    """Φ_GraSP = Compile(𝓢) → DAG"""

    def test_empty_skills(self):
        """空技能列表"""
        dag = calculate_grasp_compile([])
        assert dag["compiled"] is True
        assert dag["skill_count"] == 0
        assert dag["nodes"] == []
        assert dag["edges"] == []

    def test_single_skill(self):
        """单技能"""
        dag = calculate_grasp_compile(["skill_001"])
        assert dag["compiled"] is True
        assert dag["skill_count"] == 1

    def test_multiple_skills(self):
        """多技能"""
        skills = ["skill_001", "skill_002", "skill_003"]
        dag = calculate_grasp_compile(skills)
        assert dag["compiled"] is True
        assert dag["skill_count"] == 3

    def test_skill_count_matches(self):
        """技能数量一致性"""
        skills = [f"skill_{i:03d}" for i in range(10)]
        dag = calculate_grasp_compile(skills)
        assert dag["skill_count"] == len(skills)


class TestGraSPLocalFix:
    """𝒢' = 𝒢 ⊙ {RETRY, SUBSTITUTE, INSERT, DELETE, BACKTRACK}"""

    def test_valid_operator_retry(self):
        assert grasp_local_fix({}, "RETRY") is True

    def test_valid_operator_substitute(self):
        assert grasp_local_fix({}, "SUBSTITUTE") is True

    def test_valid_operator_insert(self):
        assert grasp_local_fix({}, "INSERT") is True

    def test_valid_operator_delete(self):
        assert grasp_local_fix({}, "DELETE") is True

    def test_valid_operator_backtrack(self):
        assert grasp_local_fix({}, "BACKTRACK") is True

    def test_invalid_operator(self):
        assert grasp_local_fix({}, "INVALID_OP") is False
        assert grasp_local_fix({}, "") is False


# ============================================================
# Core 计算器集成测试
# ============================================================

class TestApexCalculator:
    """ApexCalculator 端到端测试"""

    def test_default_calculation(self):
        """默认参数完整计算"""
        calc = ApexCalculator()
        result = calc.calculate()
        assert isinstance(result, float)
        assert result > 0

    def test_evolution_score(self):
        """进化得分在 [0,1] 范围内"""
        calc = ApexCalculator()
        score = calc.evolution_score()
        assert 0.0 <= score <= 1.0

    def test_evolution_score_with_delta_g(self):
        """指定 delta_g 计算进化得分"""
        calc = ApexCalculator()
        score = calc.evolution_score(delta_g=10.0)
        assert 0.0 <= score <= 1.0

    def test_summary_includes_keys(self):
        """summary 返回必要字段"""
        calc = ApexCalculator()
        summary = calc.summary()
        required_keys = [
            "delta_g",
            "evolution_score",
            "theta_llm",
            "k_master",
            "epsilon_self_repair",
            "phi_cycle",
            "psi_host",
        ]
        for key in required_keys:
            assert key in summary, f"Missing key: {key}"

    def test_h_zero_raises(self):
        """H_real=0 抛出异常"""
        calc = ApexCalculator()
        calc.params.h_real = 0.0
        with pytest.raises(ValueError):
            calc.calculate()

    def test_t_zero_raises(self):
        """T_iteration=0 抛出异常"""
        calc = ApexCalculator()
        calc.params.t_iteration = 0.0
        with pytest.raises(ValueError):
            calc.calculate()

    def test_updated_params(self):
        """参数更新后结果变化"""
        calc = ApexCalculator()
        r1 = calc.calculate()

        calc2 = ApexCalculator()
        calc2.params.lambda_root = 0.99
        r2 = calc2.calculate()
        assert r2 != r1


class TestSubComponents:
    """子组件独立测试"""

    def test_llm_agent_theta(self):
        """Θ_llm-agent = (λ × μ × σ) / (γ + 1)"""
        params = LlmAgentParams(
            lambda_single_call=0.9,
            mu_multi_task=0.8,
            sigma_high_quality=0.85,
            gamma_llm_cost=0.1,
        )
        expected = (0.9 * 0.8 * 0.85) / (0.1 + 1.0)
        assert abs(params.calculate_theta() - expected) < 1e-6

    def test_master_k_master_safe(self):
        """K_master safe模式 τ收敛约束"""
        params = MasterParams(
            k_code=1.0,
            tau_transfer=[0.1, 0.05, 0.08],
            upsilon_apply=0.9,
        )
        result = params.calculate_k_master(safe=True)
        assert isinstance(result, float)
        assert result > 0

    def test_self_repair_epsilon(self):
        """ε_self-repair 计算"""
        params = SelfRepairParams(g_target=100.0, g_actual=95.0)
        result = params.calculate_epsilon()
        assert result >= 1.0  # ε >= 1

    def test_self_repair_zero_actual_returns_inf(self):
        """G_actual=0 时 ε 返回无穷"""
        params = SelfRepairParams(g_target=100.0, g_actual=0.0)
        result = params.calculate_epsilon()
        assert result == float("inf")

    def test_cycle_phi_safe_caps_at_e7(self):
        """Φ_cycle safe模式上限 e^7"""
        params = CycleParams(eta_skill_up=10.0, rho_result_feedback=10.0)
        result = params.calculate_phi(safe=True)
        assert result == pytest.approx(math.exp(7.0), rel=1e-6)

    def test_host_psi_product(self):
        """Ψ_host = Ψ_mem × Ψ_app × Ψ_disk × Ω_dawn"""
        params = HostHealthParams(
            psi_mem=0.98,
            psi_app=0.99,
            psi_disk=0.97,
            omega_dawn=1.0,
        )
        expected = 0.98 * 0.99 * 0.97 * 1.0
        assert abs(params.calculate_psi() - expected) < 1e-6


class TestCalculateDeltaGConvenience:
    """calculate_delta_g 便捷函数"""

    def test_returns_float(self):
        result = calculate_delta_g({})
        assert isinstance(result, float)

    def test_accepts_params(self):
        result = calculate_delta_g({"lambda_root": 0.9, "h_real": 0.3})
        assert isinstance(result, float)


class TestVersion:
    """版本校验"""

    def test_version_exists(self):
        assert __version__ == "10.2.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
