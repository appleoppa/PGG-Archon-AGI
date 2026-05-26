"""SKILL格式生成器 - 生成墨羽可学习的SKILL"""
from typing import Dict, List
from datetime import datetime


class SkillGenerator:
    """生成SKILL.md格式"""
    
    def generate(self, strategy: Dict) -> str:
        """生成SKILL.md内容"""
        name = strategy.get('name', 'unknown')
        content = f"""# SKILL - {name}

## 描述
{strategy.get('strategy', '无描述')}

## 来源
- 基因名称: {name}
- 适应度: {strategy.get('fitness', 0.0)}

## 参数
{self._format_params(strategy.get('parameters', {}))}

## 使用场景
适用本SKILL的典型场景说明。

## 使用方法
```python
# 示例代码
```

## 注意事项
- 使用前请确认参数
- 适合的场景：{name}
"""
        return content
    
    def _format_params(self, params: Dict) -> str:
        """格式化参数"""
        if not params:
            return "无特定参数"
        return "\n".join([f"- {k}: {v}" for k, v in params.items()])


# ═════════════════════════════════════════════════════════════════════════════
# APEX V10.3 自我演化模块 - GeneNexus 集成
# Φ_APEX^∞ = ΔG_base × T_e × Ξ_S × A_m × ... × (Ψ_self × ∇_self × Ξ_repair × Γ_awake)
# ═════════════════════════════════════════════════════════════════════════════

import math

E_APEX = math.e


def apex_psi_self(phi_current: float, phi_history: list) -> float:
    """Ψ_self = σ(Φ - E[Φ]) 自我感知"""
    if not phi_history:
        return 0.5
    expected = sum(phi_history) / len(phi_history)
    diff = max(min(phi_current - expected, 10.0), -10.0)
    return 1.0 / (1.0 + E_APEX ** (-diff))


def apex_nabla_self(defect_scores: list) -> float:
    """∇_self = gradient(Defect) 自我问题发现"""
    if len(defect_scores) < 2:
        return 0.0
    total = sum(defect_scores[i] - defect_scores[i-1] for i in range(1, len(defect_scores)))
    return max(min(total / (len(defect_scores) - 1), 1.0), -1.0)


def apex_xi_repair(integral: float) -> float:
    """Ξ_repair = 1 - exp(-∫∇_self dt)"""
    return 1.0 - E_APEX ** (-max(integral, 0.0))


def apex_gamma_awake(phi_t: float, phi_0: float = 1.0) -> float:
    """Γ_awake = lim(t→∞) Φ(t)/Φ(0)"""
    if phi_0 <= 0:
        return 1.0
    ratio = phi_t / phi_0
    return ratio if ratio < 1000 else math.log(1 + ratio)


class ApexV103SkillEvolver:
    """APEX V10.3 技能演化器 - 基于GeneNexus基因读取"""

    def __init__(self, skill_quality_baseline: float = 0.7):
        self.quality_baseline = skill_quality_baseline
        self.phi_history = []
        self.defect_scores = []
        self.repair_integral = 0.0

    def evolve_skill_with_apex(self, gene_signals: dict, current_quality: float) -> dict:
        """使用APEX V10.3公式评估并演化技能"""
        # 计算基础Φ值
        signal_strength = gene_signals.get("signal_strength", 0.5)
        phi_base = current_quality * signal_strength * self.quality_baseline

        # 更新历史
        self.phi_history.append(phi_base)
        if len(self.phi_history) > 100:
            self.phi_history.pop(0)

        # 计算V10.3四模块
        psi = apex_psi_self(phi_base, self.phi_history)
        nabla = apex_nabla_self(self.defect_scores)
        xi = apex_xi_repair(self.repair_integral)
        gamma = apex_gamma_awake(phi_base)

        # 演化增益
        evolution_multiplier = psi * (1 + nabla) * xi * gamma
        evolved_quality = min(phi_base * evolution_multiplier, 1.0)

        return {
            "base_quality": current_quality,
            "phi_base": phi_base,
            "psi_self": psi,
            "nabla_self": nabla,
            "xi_repair": xi,
            "gamma_awake": gamma,
            "evolved_quality": evolved_quality,
            "evolution_gain": evolved_quality - current_quality,
        }

    def record_defect(self, score: float):
        self.defect_scores.append(max(min(score, 1.0), 0.0))
        if len(self.defect_scores) > 50:
            self.defect_scores.pop(0)

    def record_repair(self, amount: float):
        self.repair_integral = self.repair_integral * 0.95 + amount
