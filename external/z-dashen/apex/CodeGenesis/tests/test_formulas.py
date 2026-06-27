"""CodeGenesis 测试套件 - 8大公式真实测试"""
import pytest
from core.formula_core import (
    CodeGenesis, FormulaResult, quick_phi_score, CodeQualityReport
)


class TestPhiCode:
    """Φ_code 核心公式测试"""
    
    def test_normal_case(self):
        """正常情况"""
        result = CodeGenesis.calc_phi_code(
            E_std=0.9, Psi_logic=0.8, Theta_check=0.85, Gamma_task=0.9, Omega_aware=0.85, alpha_best=0.9,
            R_dup=0.1, B_bug=0.05, C_chaos=0.1, delta_ctx=0.1, mu_loss=0.1
        )
        assert result.is_valid
        assert result.value > 0
    
    def test_zero_denominator(self):
        """零分母情况"""
        result = CodeGenesis.calc_phi_code(
            E_std=1.0, Psi_logic=1.0, Theta_check=1.0, Gamma_task=1.0, Omega_aware=1.0, alpha_best=1.0,
            R_dup=0.0, B_bug=0.0, C_chaos=0.0, delta_ctx=0.0, mu_loss=0.0
        )
        assert not result.is_valid
    
    def test_optimal_case(self):
        """最优情况"""
        result = CodeGenesis.calc_phi_code(
            E_std=1.0, Psi_logic=1.0, Theta_check=1.0, Gamma_task=1.0, Omega_aware=1.0, alpha_best=1.0,
            R_dup=0.01, B_bug=0.01, C_chaos=0.01, delta_ctx=0.01, mu_loss=0.01
        )
        assert result.is_valid
        assert result.value > 1e8  # 1/1e-10


class TestOmegaPurge:
    """Ω_purge 去重净化公式测试"""
    
    def test_no_repeat(self):
        """无重复"""
        result = CodeGenesis.calc_omega_purge(S_repeat=0, S_total=100, sigma_merge=0.5)
        assert result.value == 1.0
    
    def test_full_repeat(self):
        """完全重复"""
        result = CodeGenesis.calc_omega_purge(S_repeat=100, S_total=100, sigma_merge=1.0)
        assert result.value == 0.0
    
    def test_partial_repeat(self):
        """部分重复"""
        result = CodeGenesis.calc_omega_purge(S_repeat=30, S_total=100, sigma_merge=1.0)
        assert 0.6 < result.value < 0.8


class TestPsiLogic:
    """Ψ_logic 逻辑连贯公式测试"""
    
    def test_full_coverage(self):
        """全层覆盖"""
        result = CodeGenesis.calc_psi_logic(H_layer=1.0, B_branch=1.0, E_edge=1.0, S_safe=1.0)
        assert result.value == 1.0
    
    def test_partial(self):
        """部分覆盖"""
        result = CodeGenesis.calc_psi_logic(H_layer=0.8, B_branch=0.9, E_edge=0.85, S_safe=0.9)
        assert 0.5 < result.value < 0.7


class TestQuickPhiScore:
    """快速Φ评分测试"""
    
    def test_best_case(self):
        """最佳情况"""
        score = quick_phi_score(
            dup_rate=0.01, bug_rate=0.01, chaos=0.01,
            ctx_loss=0.01, info_loss=0.01
        )
        assert score > 1e8
    
    def test_typical_case(self):
        """典型情况"""
        score = quick_phi_score(
            dup_rate=0.1, bug_rate=0.05, chaos=0.1,
            ctx_loss=0.1, info_loss=0.1
        )
        assert 1e5 < score < 3e5


class TestCodeQualityReport:
    """代码质量报告测试"""
    
    def test_production_ready(self):
        """生产级别"""
        report = CodeQualityReport(
            phi_code=100.0,
            omega_purge=0.85,
            psi_logic=0.75,
            theta_break=0.85,
            gamma_task=0.8,
            lambda_evol=0.9,
            delta_ctx=0.8,
            sigma_converge=True
        )
        assert report.is_production_ready()
    
    def test_not_ready(self):
        """未达生产级别"""
        report = CodeQualityReport(
            phi_code=10.0,
            omega_purge=0.6,
            psi_logic=0.5,
            theta_break=0.6,
            gamma_task=0.6,
            lambda_evol=0.6,
            delta_ctx=0.5,
            sigma_converge=False
        )
        assert not report.is_production_ready()


class TestThetaBreak:
    """Θ_break 断点防护公式测试"""

    def test_normal_case(self):
        """正常情况"""
        result = CodeGenesis.calc_theta_break(coverage=0.9, depth=0.85, safety=0.95)
        assert result.is_valid
        assert 0.6 < result.value < 0.8

    def test_full_coverage(self):
        """全覆盖情况"""
        result = CodeGenesis.calc_theta_break(coverage=1.0, depth=1.0, safety=1.0)
        assert result.value == 1.0

    def test_zero_safety(self):
        """零安全系数"""
        result = CodeGenesis.calc_theta_break(coverage=0.9, depth=0.85, safety=0.0)
        assert result.value == 0.0


class TestGammaTask:
    """Γ_task 任务分解公式测试"""

    def test_normal_case(self):
        """正常情况"""
        result = CodeGenesis.calc_gamma_task(decompose=0.8, parallel=0.85, quality=0.9)
        assert result.is_valid
        assert 0.5 < result.value < 0.7

    def test_optimal_case(self):
        """最优情况"""
        result = CodeGenesis.calc_gamma_task(decompose=1.0, parallel=1.0, quality=1.0)
        assert result.value == 1.0

    def test_zero_decompose(self):
        """零分解率"""
        result = CodeGenesis.calc_gamma_task(decompose=0.0, parallel=0.85, quality=0.9)
        assert result.value == 0.0


class TestLambdaEvol:
    """Λ_evol 进化系数公式测试"""

    def test_normal_case(self):
        """正常情况"""
        result = CodeGenesis.calc_lambda_evol(selection=0.85, mutation=0.9, crossover=0.88)
        assert result.is_valid
        assert 0.5 < result.value < 0.8

    def test_optimal_case(self):
        """最优情况"""
        result = CodeGenesis.calc_lambda_evol(selection=1.0, mutation=1.0, crossover=1.0)
        assert result.value == 1.0

    def test_zero_mutation(self):
        """零变异率"""
        result = CodeGenesis.calc_lambda_evol(selection=0.85, mutation=0.0, crossover=0.88)
        assert result.value == 0.0


class TestDeltaCtx:
    """Δ_ctx 上下文维护公式测试"""

    def test_normal_case(self):
        """正常情况"""
        result = CodeGenesis.calc_delta_ctx(compress=0.85, sequence=0.9, chunk=0.8, retain=0.88)
        assert result.is_valid
        assert 0.4 < result.value < 0.7

    def test_full_retention(self):
        """全保留情况"""
        result = CodeGenesis.calc_delta_ctx(compress=1.0, sequence=1.0, chunk=1.0, retain=1.0)
        assert result.value == 1.0

    def test_zero_compress(self):
        """零压缩率"""
        result = CodeGenesis.calc_delta_ctx(compress=0.0, sequence=0.9, chunk=0.8, retain=0.88)
        assert result.value == 0.0


class TestSigmaConverge:
    """Σ_conv 收敛判定公式测试"""

    def test_converged(self):
        """已收敛情况"""
        result = CodeGenesis.calc_sigma_converge(delta_prev=1.0, delta_curr=1.0005, threshold=0.001)
        assert result.is_valid
        assert result.value < 0.001

    def test_not_converged(self):
        """未收敛情况"""
        result = CodeGenesis.calc_sigma_converge(delta_prev=1.0, delta_curr=1.5, threshold=0.001)
        assert not result.is_valid
        assert result.warning == "未收敛"

    def test_exact_zero(self):
        """完全相等"""
        result = CodeGenesis.calc_sigma_converge(delta_prev=0.5, delta_curr=0.5, threshold=0.001)
        assert result.is_valid
        assert result.value == 0.0
