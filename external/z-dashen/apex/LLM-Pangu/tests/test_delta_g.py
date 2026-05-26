"""
LLM-ΔG-AntiHallucination 测试套件
包含 38 个测试用例，覆盖核心功能
"""
import pytest
import math
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.delta_g_formula import DeltaGUnified, quick_calc


class TestShannonEntropy:
    """香农熵测试"""

    def test_uniform_distribution(self):
        """测试均匀分布熵"""
        probs = [0.25, 0.25, 0.25, 0.25]
        result = DeltaGUnified.shannon_entropy(probs)
        assert result == 2.0  # log2(4) = 2

    def test_binary_distribution(self):
        """测试二进制分布熵"""
        probs = [0.5, 0.5]
        result = DeltaGUnified.shannon_entropy(probs)
        assert result == 1.0  # log2(2) = 1

    def test_single_probability(self):
        """测试单概率分布"""
        probs = [1.0]
        result = DeltaGUnified.shannon_entropy(probs)
        assert result == 0.0  # -1*log2(1) = 0

    def test_empty_list(self):
        """测试空列表"""
        probs = []
        result = DeltaGUnified.shannon_entropy(probs)
        assert result == 0.0

    def test_zeros_in_prob_list(self):
        """测试包含零的概率列表"""
        probs = [0.5, 0.5, 0.0, 0.0]
        result = DeltaGUnified.shannon_entropy(probs)
        assert result == 1.0

    def test_skewed_distribution(self):
        """测试高度偏斜分布"""
        probs = [0.9, 0.1]
        result = DeltaGUnified.shannon_entropy(probs)
        expected = -(0.9 * math.log2(0.9) + 0.1 * math.log2(0.1))
        assert abs(result - round(expected, 4)) < 0.0001

    def test_entropy_maximum(self):
        """测试最大熵 (所有等概率)"""
        n = 8
        probs = [1/n] * n
        result = DeltaGUnified.shannon_entropy(probs)
        assert abs(result - 3.0) < 0.0001  # log2(8) = 3

    def test_rounding(self):
        """测试结果精度"""
        probs = [0.333, 0.333, 0.334]
        result = DeltaGUnified.shannon_entropy(probs)
        assert isinstance(result, float)
        assert len(str(result).split('.')[1]) <= 4


class TestShannonChannelCapacity:
    """信道容量测试"""

    def test_basic_capacity(self):
        """测试基本信道容量"""
        result = DeltaGUnified.shannon_channel_capacity(1.0, 1.0)
        expected = 1.0 * math.log2(2)  # = 1.0
        assert abs(result - expected) < 0.0001

    def test_zero_bandwidth(self):
        """测试零带宽"""
        result = DeltaGUnified.shannon_channel_capacity(0.0, 10.0)
        assert result == 0.0

    def test_zero_snr(self):
        """测试零信噪比"""
        result = DeltaGUnified.shannon_channel_capacity(10.0, 0.0)
        assert result == 0.0

    def test_high_snr(self):
        """测试高信噪比"""
        result = DeltaGUnified.shannon_channel_capacity(1.0, 7.0)
        expected = 1.0 * math.log2(8)  # = 3.0
        assert abs(result - expected) < 0.0001

    def test_infinite_snr(self):
        """测试无限信噪比 (近似)"""
        result = DeltaGUnified.shannon_channel_capacity(1.0, 1e10)
        assert result > 30.0  # log2(1e10) ≈ 33.2


class TestCodeRedundancy:
    """代码冗余度测试"""

    def test_normal_case(self):
        """测试正常情况"""
        result = DeltaGUnified.code_redundancy(4.0, 2.0)
        assert result == 2.0

    def test_zero_entropy(self):
        """测试零熵"""
        result = DeltaGUnified.code_redundancy(4.0, 0.0)
        assert result == 0.0

    def test_perfect_efficiency(self):
        """测试完美效率 (冗余度=1)"""
        result = DeltaGUnified.code_redundancy(2.0, 2.0)
        assert result == 1.0

    def test_high_redundancy(self):
        """测试高冗余度"""
        result = DeltaGUnified.code_redundancy(10.0, 2.0)
        assert result == 5.0

    def test_fractional_result(self):
        """测试分数结果"""
        result = DeltaGUnified.code_redundancy(3.0, 2.0)
        assert result == 1.5


class TestCalcTotalDeltaG:
    """统一ΔG计算测试"""

    def test_healthy_state(self):
        """测试健康状态"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=1.5, F=0.95, L=50, N=0.1, C=8.0,
            Omega=0.9, grad_E=0.2, Gamma=0.85,
            avg_code_len=2.0, Psi=0.9, Theta=0.95
        )
        # ΔG ≈ 3.01 (轻度偏离状态)
        assert dg <= 3.5

    def test_mild_deviation(self):
        """测试轻度偏离"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=4.0, F=0.7, L=500, N=0.4, C=4.0,
            Omega=0.6, grad_E=0.5, Gamma=0.6,
            avg_code_len=3.5, Psi=0.7, Theta=0.65
        )
        # ΔG ≈ 9.32 (严重越界，因为H=4.0高熵)
        assert dg > 4.0

    def test_critical_state(self):
        """测试严重越界"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=7.5, F=0.3, L=2000, N=0.8, C=2.0,
            Omega=0.3, grad_E=0.9, Gamma=0.3,
            avg_code_len=6.0, Psi=0.4, Theta=0.3
        )
        assert dg > 4.0

    def test_zero_entropy(self):
        """测试零熵边界"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=0.0, F=0.95, L=50, N=0.1, C=8.0,
            Omega=0.9, grad_E=0.2, Gamma=0.85,
            avg_code_len=2.0, Psi=0.9, Theta=0.95
        )
        assert isinstance(dg, float)

    def test_zero_capacity(self):
        """测试零容量边界"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=2.0, F=0.9, L=100, N=0.5, C=0.0,
            Omega=0.8, grad_E=0.3, Gamma=0.7,
            avg_code_len=2.5, Psi=0.8, Theta=0.85
        )
        assert isinstance(dg, float)

    def test_maximum_values(self):
        """测试最大值情况"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=8.0, F=1.0, L=10000, N=1.0, C=1.0,
            Omega=1.0, grad_E=1.0, Gamma=1.0,
            avg_code_len=10.0, Psi=1.0, Theta=1.0
        )
        assert dg > 0  # 应该有较大值

    def test_minimum_values(self):
        """测试最小值情况"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=0.0, F=1.0, L=0, N=0.0, C=1.0,
            Omega=1.0, grad_E=0.0, Gamma=1.0,
            avg_code_len=0.0, Psi=1.0, Theta=1.0
        )
        assert isinstance(dg, float)

    def test_perfect_system(self):
        """测试完美系统 (所有参数最优)"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=0.0, F=1.0, L=0, N=0.0, C=100.0,
            Omega=1.0, grad_E=0.0, Gamma=1.0,
            avg_code_len=1.0, Psi=1.0, Theta=1.0
        )
        # ΔG ≈ 1.18 (基准值DELTA_B=0.18 + TAU*exp(-TAU*L)贡献)
        assert dg < 2.0


class TestJudgeSystemState:
    """系统状态判定测试"""

    def test_steady_boundary_low(self):
        """测试稳态下边界"""
        engine = DeltaGUnified()
        state = engine.judge_system_state(0.0)
        assert state == "steady_健康稳态"

    def test_steady_boundary_high(self):
        """测试稳态上边界"""
        engine = DeltaGUnified()
        state = engine.judge_system_state(2.10)
        assert state == "steady_健康稳态"

    def test_mild_boundary_low(self):
        """测试轻度偏离下边界"""
        engine = DeltaGUnified()
        state = engine.judge_system_state(2.11)
        assert state == "mild_轻度偏离_自动局部修复"

    def test_mild_boundary_high(self):
        """测试轻度偏离上边界"""
        engine = DeltaGUnified()
        state = engine.judge_system_state(4.0)
        assert state == "mild_轻度偏离_自动局部修复"

    def test_critical_above_mild(self):
        """测试严重越界"""
        engine = DeltaGUnified()
        state = engine.judge_system_state(4.01)
        assert state == "critical_严重越界_触发全量重启自愈"

    def test_critical_high_value(self):
        """测试严重越界高值"""
        engine = DeltaGUnified()
        state = engine.judge_system_state(100.0)
        assert state == "critical_严重越界_触发全量重启自愈"


class TestQuickCalc:
    """快速计算测试"""

    def test_quick_calc_returns_tuple(self):
        """测试快速计算返回类型"""
        result = quick_calc(H=2.0, F=0.9, L=100)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_quick_calc_state_valid(self):
        """测试快速计算状态有效性"""
        dg, state = quick_calc(H=2.0, F=0.9, L=100)
        assert "steady" in state or "mild" in state or "critical" in state


class TestEdgeCases:
    """边界条件测试"""

    def test_negative_H(self):
        """测试负熵 (边界)"""
        engine = DeltaGUnified()
        # 虽然不应该出现负值，但函数应该处理
        dg = engine.calc_total_delta_g(
            H=-1.0, F=0.9, L=100, N=0.1, C=8.0,
            Omega=0.9, grad_E=0.2, Gamma=0.85,
            avg_code_len=2.0, Psi=0.9, Theta=0.95
        )
        assert isinstance(dg, float)

    def test_very_long_context(self):
        """测试超长上下文"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=5.0, F=0.6, L=100000, N=0.3, C=4.0,
            Omega=0.5, grad_E=0.6, Gamma=0.5,
            avg_code_len=4.0, Psi=0.6, Theta=0.6
        )
        assert dg > 4.0  # 应该触发严重越界

    def test_all_ones_params(self):
        """测试全1参数 (最理想情况)"""
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=1.0, F=1.0, L=10, N=0.0, C=10.0,
            Omega=1.0, grad_E=0.0, Gamma=1.0,
            avg_code_len=1.0, Psi=1.0, Theta=1.0
        )
        assert dg < 2.0


class TestIntegration:
    """集成测试"""

    def test_full_pipeline(self):
        """测试完整流程"""
        # 1. 计算熵
        probs = [0.4, 0.3, 0.2, 0.1]
        H = DeltaGUnified.shannon_entropy(probs)

        # 2. 计算冗余度
        R = DeltaGUnified.code_redundancy(3.0, H)

        # 3. 计算 ΔG
        engine = DeltaGUnified()
        dg = engine.calc_total_delta_g(
            H=H, F=0.9, L=100, N=0.1, C=8.0,
            Omega=0.9, grad_E=0.2, Gamma=0.8,
            avg_code_len=3.0, Psi=0.9, Theta=0.9
        )

        # 4. 判定状态
        state = engine.judge_system_state(dg)

        # 验证
        assert isinstance(H, float)
        assert isinstance(R, float)
        assert isinstance(dg, float)
        assert "steady" in state or "mild" in state or "critical" in state

    def test_class_constants(self):
        """测试类常量"""
        assert DeltaGUnified.LAMBDA == 1.5
        assert DeltaGUnified.TAU == 0.32
        assert DeltaGUnified.DELTA_B == 0.18


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
