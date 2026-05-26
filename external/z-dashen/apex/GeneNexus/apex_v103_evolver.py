"""APEX V10.3 技能演化器"""
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
    """APEX V10.3 技能演化器"""

    def __init__(self, skill_quality_baseline: float = 0.7):
        self.quality_baseline = skill_quality_baseline
        self.phi_history = []
        self.defect_scores = []
        self.repair_integral = 0.0

    def evolve_skill_with_apex(self, gene_signals: dict, current_quality: float) -> dict:
        signal_strength = gene_signals.get("signal_strength", 0.5)
        phi_base = current_quality * signal_strength * self.quality_baseline
        
        self.phi_history.append(phi_base)
        if len(self.phi_history) > 100:
            self.phi_history.pop(0)

        psi = apex_psi_self(phi_base, self.phi_history)
        nabla = apex_nabla_self(self.defect_scores)
        xi = apex_xi_repair(self.repair_integral)
        gamma = apex_gamma_awake(phi_base)

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
