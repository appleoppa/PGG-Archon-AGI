"""
CodeGenesis 核心公式实现
8重闭环公式真实代码，无模拟

公式体系：
1. Φ_code   - 代码质量综合评估公式
2. Ω_purge  - 去重净化公式
3. Ψ_logic  - 逻辑连贯性公式
4. Θ_break  - 断点防护公式
5. Γ_task   - 任务分解公式
6. Λ_evol   - 进化系数公式
7. Δ_ctx    - 上下文维护公式
8. Σ_conv   - 收敛判定公式
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import math


@dataclass
class FormulaResult:
    """公式计算结果"""
    name: str
    value: float
    description: str = ""
    is_valid: bool = True
    warning: Optional[str] = None


class CodeGenesis:
    """代码觉醒公式核心"""
    
    LAMBDA = 1.5  # 演化系数
    
    @staticmethod
    def calc_phi_code(E_std: float, Psi_logic: float, Theta_check: float,
                       Gamma_task: float, Omega_aware: float, alpha_best: float,
                       R_dup: float, B_bug: float, C_chaos: float,
                       delta_ctx: float, mu_loss: float) -> FormulaResult:
        """
        核心公式: Φ_code = (E_std × Ψ_logic × Θ_check × Γ_task × Ω_aware × α_best) / (R_dup × B_bug × C_chaos × δ_ctx × μ_loss)
        """
        if min(R_dup, B_bug, C_chaos, delta_ctx, mu_loss) <= 0:
            return FormulaResult(
                name="Φ_code",
                value=float('inf'),
                description="无效参数：分母不能为0或负数",
                is_valid=False,
                warning="参数错误"
            )
        
        numerator = E_std * Psi_logic * Theta_check * Gamma_task * Omega_aware * alpha_best
        denominator = R_dup * B_bug * C_chaos * delta_ctx * mu_loss
        value = numerator / denominator
        
        desc = f"E_std={E_std}, Psi={Psi_logic}, Theta={Theta_check}, Γ={Gamma_task}, Ω={Omega_aware}, α={alpha_best} | R_dup={R_dup}, B={B_bug}, C={C_chaos}, δ={delta_ctx}, μ={mu_loss}"
        
        return FormulaResult(name="Φ_code", value=value, description=desc)
    
    @staticmethod
    def calc_omega_purge(S_repeat: float, S_total: float, sigma_merge: float) -> FormulaResult:
        """去重净化公式: Ω_purge = 1 - (S_repeat/S_total) × σ_merge"""
        if S_total <= 0:
            return FormulaResult(
                name="Ω_purge",
                value=1.0,
                description="无可用代码总量",
                warning="S_total无效"
            )
        
        value = 1 - (S_repeat / S_total) * sigma_merge
        value = max(0.0, min(1.0, value))  # 限制在[0,1]
        
        return FormulaResult(
            name="Ω_purge",
            value=value,
            description=f"S_repeat={S_repeat}, S_total={S_total}, σ={sigma_merge}"
        )
    
    @staticmethod
    def calc_psi_logic(H_layer: float, B_branch: float, E_edge: float, S_safe: float) -> FormulaResult:
        """逻辑连贯公式: Ψ_logic = H_layer × B_branch × E_edge × S_safe"""
        value = H_layer * B_branch * E_edge * S_safe
        return FormulaResult(
            name="Ψ_logic",
            value=value,
            description=f"H={H_layer}, B={B_branch}, E={E_edge}, S={S_safe}"
        )
    
    @staticmethod
    def calc_theta_break(coverage: float, depth: float, safety: float) -> FormulaResult:
        """断点防护公式: Θ_break = coverage × depth × safety"""
        value = coverage * depth * safety
        return FormulaResult(
            name="Θ_break",
            value=value,
            description=f"coverage={coverage}, depth={depth}, safety={safety}"
        )
    
    @staticmethod
    def calc_gamma_task(decompose: float, parallel: float, quality: float) -> FormulaResult:
        """任务分解公式: Γ_task = decompose × parallel × quality"""
        value = decompose * parallel * quality
        return FormulaResult(
            name="Γ_task",
            value=value,
            description=f"decompose={decompose}, parallel={parallel}, quality={quality}"
        )
    
    @staticmethod
    def calc_lambda_evol(selection: float, mutation: float, crossover: float) -> FormulaResult:
        """进化系数公式: Λ_evol = selection × mutation × crossover"""
        value = selection * mutation * crossover
        return FormulaResult(
            name="Λ_evol",
            value=value,
            description=f"selection={selection}, mutation={mutation}, crossover={crossover}"
        )
    
    @staticmethod
    def calc_delta_ctx(compress: float, sequence: float, chunk: float, retain: float) -> FormulaResult:
        """上下文维护公式: Δ_ctx = ω × τ × η × ζ"""
        value = compress * sequence * chunk * retain
        return FormulaResult(
            name="Δ_ctx",
            value=value,
            description=f"ω={compress}, τ={sequence}, η={chunk}, ζ={retain}"
        )
    
    @staticmethod
    def calc_sigma_converge(delta_prev: float, delta_curr: float, threshold: float = 0.001) -> FormulaResult:
        """收敛判定公式: Σ_conv = |Δ_new - Δ_old| < ε"""
        diff = abs(delta_curr - delta_prev)
        is_converged = diff < threshold
        
        return FormulaResult(
            name="Σ_conv",
            value=diff,
            description=f"diff={diff:.6f}, threshold={threshold}, converged={is_converged}",
            is_valid=is_converged,
            warning=None if is_converged else "未收敛"
        )


def quick_phi_score(dup_rate: float = 0.1, bug_rate: float = 0.05,
                     chaos: float = 0.1, ctx_loss: float = 0.1,
                     info_loss: float = 0.1) -> float:
    """
    快速Φ评分
    Φ = 1 / (dup_rate × bug_rate × chaos × ctx_loss × info_loss)
    """
    denominator = dup_rate * bug_rate * chaos * ctx_loss * info_loss
    if denominator <= 0:
        return float('inf')
    return 1.0 / denominator


@dataclass
class CodeQualityReport:
    """代码质量综合报告"""
    phi_code: float
    omega_purge: float
    psi_logic: float
    theta_break: float
    gamma_task: float
    lambda_evol: float
    delta_ctx: float
    sigma_converge: bool
    
    def overall_score(self) -> float:
        """综合评分"""
        return (self.phi_code * self.omega_purge * self.psi_logic * 
                self.theta_break * self.gamma_task * self.lambda_evol * self.delta_ctx)
    
    def is_production_ready(self) -> bool:
        """是否达到生产级别"""
        return (self.omega_purge > 0.8 and 
                self.psi_logic > 0.7 and
                self.theta_break > 0.8 and
                self.sigma_converge)
