"""
ApexSpiral 核心计算模块
实现了 APEX V10 终极闭环进化公式的 Python 版本
"""

import math
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class LlmAgentParams:
    """单LLM多任务Agent效能参数"""
    lambda_single_call: float = 0.9   # λ 单次调用质量系数
    mu_multi_task: float = 0.85       # μ 多任务并行系数
    sigma_high_quality: float = 0.88  # σ 高质量输出系数
    gamma_llm_cost: float = 0.1       # γ LLM调用成本系数

    def calculate_theta(self) -> float:
        """Θ_llm-agent = (λ × μ × σ) / (γ + 1)"""
        return (self.lambda_single_call * self.mu_multi_task * self.sigma_high_quality) / (self.gamma_llm_cost + 1.0)


@dataclass
class MasterParams:
    """公式通解+技能全域掌握参数"""
    k_code: float = 1.0                        # K_code 编码掌握系数
    tau_transfer: List[float] = field(default_factory=lambda: [0.1, 0.05, 0.08])  # τ_transfer^i
    upsilon_apply: float = 0.9               # υ_apply 技能应用系数

    def calculate_k_master(self, safe: bool = True) -> float:
        """K_master = K_code × (1 + Στ) × υ_apply"""
        if safe:
            # V8.2 safe版：τ收敛约束
            sum_tau_converged = sum(t / (1.0 - min(max(t, 0.0), 0.99)) for t in self.tau_transfer)
            return self.k_code * (1.0 + sum_tau_converged) * self.upsilon_apply
        else:
            sum_tau = sum(self.tau_transfer)
            return self.k_code * (1.0 + sum_tau) * self.upsilon_apply


@dataclass
class SelfRepairParams:
    """全场景自主深度修复参数"""
    g_target: float = 100.0      # G_target 目标增益
    g_actual: float = 95.0      # G_actual 实际增益
    delta_error_locate: float = 1.0  # δ 错误定位效率系数
    psi_thorough_fix: float = 1.0   # ψ 彻底修复系数
    kappa_no_repeat: float = 1.0     # κ 防复发系数

    def calculate_epsilon(self) -> float:
        """ε_self-repair = 1 + |(Gt - Ga)/Ga| × δ × ψ × κ"""
        if self.g_actual == 0.0:
            return float('inf')
        relative_error = abs((self.g_target - self.g_actual) / self.g_actual)
        return 1.0 + relative_error * self.delta_error_locate * self.psi_thorough_fix * self.kappa_no_repeat


@dataclass
class CycleParams:
    """正向循环反馈增益参数"""
    eta_skill_up: float = 0.5       # η 技能提升系数
    rho_result_feedback: float = 0.5  # ρ 结果反馈系数

    def calculate_phi(self, safe: bool = True) -> float:
        """Φ_cycle = e^(η × ρ)"""
        product = self.eta_skill_up * self.rho_result_feedback
        if safe:
            # V8.2 safe版：上限保护 e^7 ≈ 1096
            product = min(product, 7.0)
        return math.exp(product)


@dataclass
class HostHealthParams:
    """主机全维度健康稳态参数"""
    psi_mem: float = 0.98    # Ψ_mem 内存健康系数
    psi_app: float = 0.99    # Ψ_app 应用健康系数
    psi_disk: float = 0.97   # Ψ_disk 磁盘健康系数
    omega_dawn: float = 1.0  # Ω_dawn 启动就绪系数

    def calculate_psi(self) -> float:
        """Ψ_host = Ψ_mem × Ψ_app × Ψ_disk × Ω_dawn"""
        return self.psi_mem * self.psi_app * self.psi_disk * self.omega_dawn


@dataclass
class ApexParams:
    """APEX V10 全量参数容器"""
    lambda_root: float = 0.95              # Λ_root 本源务实基因系数
    xi_anti_hallucination: float = 1.0    # ξ 幻觉零容忍系数
    h_real: float = 0.5                   # H_real 真实有效信息熵
    t_iteration: float = 2.0              # T 迭代周期

    llm_agent: LlmAgentParams = field(default_factory=LlmAgentParams)
    master: MasterParams = field(default_factory=MasterParams)
    self_repair: SelfRepairParams = field(default_factory=SelfRepairParams)
    cycle: CycleParams = field(default_factory=CycleParams)
    host: HostHealthParams = field(default_factory=HostHealthParams)


class ApexCalculator:
    """APEX 公式计算器"""

    def __init__(self, params: Optional[ApexParams] = None):
        self.params = params or ApexParams()

    def calculate(self, params: Optional[Dict[str, Any]] = None) -> float:
        """
        计算 ΔG_ultimate

        ΔG = (Λ_root × Θ × K × ξ × Ψ_host × Φ_cycle) / (H × T × ε)
        """
        if params:
            self._update_params(params)

        if self.params.h_real <= 0:
            raise ValueError("H_real must be > 0")
        if self.params.t_iteration <= 0:
            raise ValueError("T_iteration must be > 0")

        theta = self.params.llm_agent.calculate_theta()
        k_master = self.params.master.calculate_k_master(safe=True)
        epsilon = self.params.self_repair.calculate_epsilon()
        phi = self.params.cycle.calculate_phi(safe=True)
        psi = self.params.host.calculate_psi()

        if epsilon == 0:
            raise ValueError("ε_self-repair cannot be 0")

        numerator = (self.params.lambda_root
                    * theta
                    * k_master
                    * self.params.xi_anti_hallucination
                    * psi
                    * phi)

        denominator = self.params.h_real * self.params.t_iteration * epsilon

        return numerator / denominator

    def evolution_score(self, delta_g: Optional[float] = None) -> float:
        """计算进化得分，归一化到 [0, 1]"""
        if delta_g is None:
            delta_g = self.calculate()
        return delta_g / (delta_g + self.params.h_real + 1e-10)

    def _update_params(self, params: Dict[str, Any]) -> None:
        """从字典更新参数"""
        if 'lambda_root' in params:
            self.params.lambda_root = params['lambda_root']
        if 'xi_anti_hallucination' in params:
            self.params.xi_anti_hallucination = params['xi_anti_hallucination']
        if 'h_real' in params:
            self.params.h_real = params['h_real']
        if 't_iteration' in params:
            self.params.t_iteration = params['t_iteration']

        if 'llm_agent' in params:
            for k, v in params['llm_agent'].items():
                if hasattr(self.params.llm_agent, k):
                    setattr(self.params.llm_agent, k, v)

        if 'master' in params:
            for k, v in params['master'].items():
                if k == 'tau_transfer' and isinstance(v, list):
                    self.params.master.tau_transfer = v
                elif hasattr(self.params.master, k):
                    setattr(self.params.master, k, v)

        if 'self_repair' in params:
            for k, v in params['self_repair'].items():
                if hasattr(self.params.self_repair, k):
                    setattr(self.params.self_repair, k, v)

        if 'cycle' in params:
            for k, v in params['cycle'].items():
                if hasattr(self.params.cycle, k):
                    setattr(self.params.cycle, k, v)

        if 'host' in params:
            for k, v in params['host'].items():
                if hasattr(self.params.host, k):
                    setattr(self.params.host, k, v)

    def summary(self) -> Dict[str, Any]:
        """返回计算摘要"""
        delta_g = self.calculate()
        return {
            "delta_g": delta_g,
            "evolution_score": self.evolution_score(delta_g),
            "theta_llm": self.params.llm_agent.calculate_theta(),
            "k_master": self.params.master.calculate_k_master(safe=True),
            "epsilon_self_repair": self.params.self_repair.calculate_epsilon(),
            "phi_cycle": self.params.cycle.calculate_phi(safe=True),
            "psi_host": self.params.host.calculate_psi(),
        }


def calculate_delta_g(params: Dict[str, Any]) -> float:
    """便捷函数：直接计算 ΔG"""
    calc = ApexCalculator()
    return calc.calculate(params)


if __name__ == "__main__":
    # 示例
    calc = ApexCalculator()
    params = ApexParams()
    calc.params = params

    delta_g = calc.calculate()
    score = calc.evolution_score(delta_g)

    print(f"ΔG_ultimate = {delta_g:.6f}")
    print(f"Evolution Score = {score:.6f}")
