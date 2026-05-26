"""
XuanjiQuant - APEX V10.3 量化金融公式集成
融合APEX演化范式与金融量化模型

APEX V10.3 新增：
  Ψ_self = σ(Φ - E[Φ])     # 交易自我感知
  ∇_self = gradient(Defect) # 策略缺陷发现
  Ξ_repair = 1 - exp(-∫∇dt) # 策略自我修复
  Γ_awake = lim(t→∞) Φ(t)/Φ(0) # 量化觉醒进化
"""

import math
from collections import deque
from dataclasses import dataclass
from typing import Optional


E = math.e


@dataclass
class QuantApexParams:
    """APEX V10.3 量化参数"""
    # 金融基础参数
    kelly_fraction: float = 0.25      # Kelly公式 fraction
    sharpe_ratio: float = 1.5         # 夏普比率
    max_drawdown: float = 0.15        # 最大回撤
    win_rate: float = 0.55            # 胜率
    profit_factor: float = 1.8         # 盈亏比
    # APEX演化参数
    delta_g_base: float = 0.49
    signal_quality: float = 0.8
    execution_efficiency: float = 0.9


def calculate_apex_quant_score(params: QuantApexParams, phi_history: list = None) -> dict:
    """APEX V10.3 量化评分"""
    phi_history = phi_history or []

    # Kelly + 夏普 基础评分
    base_score = params.kelly_fraction * params.sharpe_ratio * params.win_rate * params.profit_factor

    # 最大回撤惩罚
    dd_penalty = 1.0 - params.max_drawdown

    # APEX V10.3 自我闭环
    if phi_history:
        expected = sum(phi_history) / len(phi_history)
        psi_self = 1.0 / (1.0 + E ** (-max(min(base_score - expected, 10.0), -10.0)))
    else:
        psi_self = 0.5

    # 核心量化APEX得分
    apex_quant = base_score * dd_penalty * params.execution_efficiency * psi_self

    return {
        "base_score": base_score,
        "dd_penalty": dd_penalty,
        "psi_self": psi_self,
        "apex_quant_score": apex_quant,
        "grade": "S+" if apex_quant > 2.0 else "S" if apex_quant > 1.5 else "A" if apex_quant > 1.0 else "B" if apex_quant > 0.5 else "C",
    }


class QuantEvolutionTracker:
    """量化策略演化追踪器"""

    def __init__(self, max_history: int = 500):
        self.phi_history = deque(maxlen=max_history)
        self.defect_history = deque(maxlen=max_history // 10)
        self.repair_history = deque(maxlen=max_history // 10)
        self.phi_0 = 1.0

    def record_phi(self, phi: float):
        if not self.phi_history:
            self.phi_0 = max(phi, 0.001)
        self.phi_history.append(phi)

    def record_defect(self, defect_score: float):
        self.defect_history.append(max(min(defect_score, 1.0), 0.0))

    def record_repair(self, amount: float, success: bool):
        self.repair_history.append((amount, success))

    def get_psi_self(self, current: float) -> float:
        if not self.phi_history:
            return 0.5
        expected = sum(self.phi_history) / len(self.phi_history)
        diff = max(min(current - expected, 10.0), -10.0)
        return 1.0 / (1.0 + E ** (-diff))

    def get_nabla_self(self) -> float:
        if len(self.defect_history) < 2:
            return 0.0
        total = sum(self.defect_history[i] - self.defect_history[i-1]
                    for i in range(1, len(self.defect_history)))
        return max(min(total / (len(self.defect_history) - 1), 1.0), -1.0)

    def get_xi_repair(self) -> float:
        if not self.repair_history:
            return 0.0
        integral = sum(a * (0.95 ** (len(self.repair_history) - i - 1))
                        for i, (a, s) in enumerate(self.repair_history) if s)
        return 1.0 - E ** (-max(integral, 0.0))

    def get_gamma_awake(self, current: float) -> float:
        if self.phi_0 <= 0 or current <= 0:
            return 1.0
        ratio = current / self.phi_0
        return ratio if ratio < 1000 else math.log(1 + ratio)

    def get_status(self, current: float) -> dict:
        psi = self.get_psi_self(current)
        nabla = self.get_nabla_self()
        xi = self.get_xi_repair()
        gamma = self.get_gamma_awake(current)
        return {
            "psi_self": psi,
            "nabla_self": nabla,
            "xi_repair": xi,
            "gamma_awake": gamma,
            "status": "🟢 健康" if xi > 0.8 else "🟡 优化中" if nabla < 0 else "🔴 需修复",
        }
