"""
CodeGenesis 核心公式实现 + APEX V10.3 增强
8重闭环公式 + APEX终极完全体

公式体系：
1. Φ_code   - 代码质量综合评估公式
2. Ω_purge  - 去重净化公式
3. Ψ_logic  - 逻辑连贯性公式
4. Θ_break  - 断点防护公式
5. Γ_task   - 任务分解公式
6. Λ_evol   - 进化系数公式
7. Δ_ctx    - 上下文维护公式
8. Σ_conv   - 收敛判定公式
9. APEX_V10 - APEX终极完全体（V10.3新增）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import math
import time
from collections import deque


# ── APEX V10.3 新增模块 ────────────────────────────────────────────────────

E = math.e


def psi_self(phi_current: float, phi_history: list) -> float:
    """Ψ_self = σ(Φ_APEX - E[Φ_APEX]) 自我感知"""
    if not phi_history:
        return 0.5
    expected = sum(phi_history) / len(phi_history)
    diff = max(min(phi_current - expected, 10.0), -10.0)
    return 1.0 / (1.0 + E ** (-diff))


def nabla_self_defect(defect_scores: list, timestamps: list) -> float:
    """∇_self = gradient(Defect) 自我问题发现"""
    if len(defect_scores) < 2:
        return 0.0
    n = len(defect_scores)
    total = 0.0
    for i in range(1, n):
        dt = max(timestamps[i] - timestamps[i-1], 1)
        total += (defect_scores[i] - defect_scores[i-1]) / dt
    return max(min(total / (n - 1), 1.0), -1.0)


def xi_repair(repair_integral: float) -> float:
    """Ξ_repair = 1 - exp(-∫∇_self dt) 自我修复闭环"""
    return 1.0 - E ** (-max(repair_integral, 0.0))


def gamma_awake(phi_t: float, phi_0: float) -> float:
    """Γ_awake = lim(t→∞) Φ_APEX(t)/Φ_APEX(0) 觉醒进化"""
    if phi_0 <= 0 or phi_t <= 0:
        return 1.0
    ratio = phi_t / phi_0
    if ratio < 1000.0:
        return ratio
    return math.log(1.0 + ratio)


@dataclass
class ApexV103Params:
    """APEX V10.3 9层参数"""
    delta_g_base: float = 0.49
    t_e: float = 1.0
    xi_s: float = 1.0
    a_m: float = 1.0
    delta_w_ij: float = 0.01
    n_sync: float = 10.0
    h_r: float = 1.0
    c_claw: float = 1.0
    v_gdp: float = 1.0
    p_opt: float = 1.0
    v_g: float = 1.0
    a_c: float = 0.85
    d_c: float = 1.0
    i_gdp: float = 1.0
    v_avo: float = 1.0
    delta_perf: float = 0.05
    eta_pipeline: float = 0.9
    eta_reg: float = 1.0
    s_x: float = 1.0
    r_parallel: float = 1.0
    delta_acc: float = 0.02
    a_ara: float = 1.0
    r_ara: float = 1.0
    u_ara: float = 1.0
    k_ara: float = 1.0
    m_mimic: float = 1.0
    lambda_scale: float = 1.0
    xi_supervise: float = 1.0
    upsilon_auto: float = 1.0


def calculate_apex_v103(params: ApexV103Params, phi_history: list = None) -> float:
    """APEX V10.3 终极完全体总公式"""
    p = params
    phi_history = phi_history or []

    l1 = p.delta_g_base * p.t_e * p.xi_s * p.a_m
    l2 = p.delta_w_ij * p.n_sync * p.h_r
    l3 = p.c_claw * p.v_gdp * p.p_opt
    l4 = p.v_g * p.a_c * p.d_c * p.i_gdp
    l5 = p.v_avo * p.delta_perf * p.eta_pipeline * p.eta_reg
    l6 = p.s_x * p.r_parallel * p.delta_acc
    l7 = p.a_ara * p.r_ara * p.u_ara * p.k_ara
    l8 = p.m_mimic * p.lambda_scale * p.xi_supervise * p.upsilon_auto

    core = l1 * l2 * l3 * l4 * l5 * l6 * l7 * l8
    psi = psi_self(core, phi_history)
    gamma = gamma_awake(core, 1.0)

    l9 = psi * 0.0 * xi_repair(0.0) * gamma  # 自我闭环层（需注入历史数据）
    return min(core * l9 if l9 != 0 else core, 1e10)


# ── 原有 CodeGenesis 公式 ─────────────────────────────────────────────────

@dataclass
class FormulaResult:
    name: str
    value: float
    description: str = ""
    is_valid: bool = True
    warning: Optional[str] = None


class CodeGenesis:
    LAMBDA = 1.5

    @staticmethod
    def calc_phi_code(E_std: float, Psi_logic: float, Theta_check: float,
                       Gamma_task: float, Omega_aware: float, alpha_best: float,
                       R_dup: float, B_bug: float, C_chaos: float,
                       delta_ctx: float, mu_loss: float) -> FormulaResult:
        if min(R_dup, B_bug, C_chaos, delta_ctx, mu_loss) <= 0:
            return FormulaResult(name="Φ_code", value=float("inf"), description="无效参数",
                                is_valid=False, warning="参数错误")
        numerator = E_std * Psi_logic * Theta_check * Gamma_task * Omega_aware * alpha_best
        denominator = R_dup * B_bug * C_chaos * delta_ctx * mu_loss
        return FormulaResult(name="Φ_code", value=numerator / denominator,
                            description=f"E={E_std}, Ψ={Psi_logic}, Θ={Theta_check}, Γ={Gamma_task}, Ω={Omega_aware}, α={alpha_best} | R={R_dup}, B={B_bug}, C={C_chaos}, δ={delta_ctx}, μ={mu_loss}")

    @staticmethod
    def calc_omega_purge(S_repeat: float, S_total: float, sigma_merge: float) -> FormulaResult:
        if S_total <= 0:
            return FormulaResult(name="Ω_purge", value=1.0, description="无可用代码总量", warning="S_total无效")
        value = max(0.0, min(1.0, 1 - (S_repeat / S_total) * sigma_merge))
        return FormulaResult(name="Ω_purge", value=value, description=f"S_repeat={S_repeat}, S_total={S_total}, σ={sigma_merge}")

    @staticmethod
    def calc_psi_logic(H_layer: float, B_branch: float, E_edge: float, S_safe: float) -> FormulaResult:
        return FormulaResult(name="Ψ_logic", value=H_layer * B_branch * E_edge * S_safe,
                            description=f"H={H_layer}, B={B_branch}, E={E_edge}, S={S_safe}")

    @staticmethod
    def calc_theta_break(coverage: float, depth: float, safety: float) -> FormulaResult:
        return FormulaResult(name="Θ_break", value=coverage * depth * safety,
                            description=f"coverage={coverage}, depth={depth}, safety={safety}")

    @staticmethod
    def calc_gamma_task(decompose: float, parallel: float, quality: float) -> FormulaResult:
        return FormulaResult(name="Γ_task", value=decompose * parallel * quality,
                            description=f"decompose={decompose}, parallel={parallel}, quality={quality}")

    @staticmethod
    def calc_lambda_evol(selection: float, mutation: float, crossover: float) -> FormulaResult:
        return FormulaResult(name="Λ_evol", value=selection * mutation * crossover,
                            description=f"selection={selection}, mutation={mutation}, crossover={crossover}")

    @staticmethod
    def calc_delta_ctx(compress: float, sequence: float, chunk: float, retain: float) -> FormulaResult:
        return FormulaResult(name="Δ_ctx", value=compress * sequence * chunk * retain,
                            description=f"ω={compress}, τ={sequence}, η={chunk}, ζ={retain}")

    @staticmethod
    def calc_sigma_converge(delta_prev: float, delta_curr: float, threshold: float = 0.001) -> FormulaResult:
        diff = abs(delta_curr - delta_prev)
        is_converged = diff < threshold
        return FormulaResult(name="Σ_conv", value=diff,
                            description=f"diff={diff:.6f}, threshold={threshold}, converged={is_converged}",
                            is_valid=is_converged, warning=None if is_converged else "未收敛")


def quick_phi_score(dup_rate: float = 0.1, bug_rate: float = 0.05,
                     chaos: float = 0.1, ctx_loss: float = 0.1,
                     info_loss: float = 0.1) -> float:
    denominator = dup_rate * bug_rate * chaos * ctx_loss * info_loss
    if denominator <= 0:
        return float("inf")
    return 1.0 / denominator


@dataclass
class CodeQualityReport:
    phi_code: float
    omega_purge: float
    psi_logic: float
    theta_break: float
    gamma_task: float
    lambda_evol: float
    delta_ctx: float
    sigma_converge: bool

    def overall_score(self) -> float:
        return (self.phi_code * self.omega_purge * self.psi_logic *
                self.theta_break * self.gamma_task * self.lambda_evol * self.delta_ctx)

    def is_production_ready(self) -> bool:
        return (self.omega_purge > 0.8 and self.psi_logic > 0.7 and
                self.theta_break > 0.8 and self.sigma_converge)
