"""
core/delta_g_formula.py - 盘古核心公式：香农信息论 + APEX演化范式 融合

底层基石：香农三大定律 + APEX ΔG 全域演化

香农三大定律：
- H(X) = -Σp(xᵢ)log₂p(xᵢ) → 信息熵
- C = Blog₂(1+S/N)          → 信道容量
- L_avg ≥ H(X)               → 无损编码

APEX ΔG 全域演化公式：
- 七大模块统一约束
- 防幻觉从根源做起
"""

import math
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[Pangu-ΔG] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class DeltaGUnified:
    """
    盘古核心公式类
    融合香农信息论三大定律与APEX演化范式
    
    Attributes:
        LAMBDA: 归一化系数，用于均衡各模块贡献
        TAU: 时间衰减因子，控制信息衰减速率
        DELTA_B: 基础偏移量，保证最小约束强度
    """
    
    LAMBDA = 1.5       # 归一化系数
    TAU = 0.32         # 时间衰减因子
    DELTA_B = 0.18      # 基础偏移量

    def __init__(self):
        """
        初始化盘古核心公式
        建立香农-APEX双底座融合框架
        """
        logger.info("盘古ΔG公式初始化 - 香农+APEX双底座融合")
        pass

    # ==================== 香农信息论三大定律 ====================
    
    @staticmethod
    def shannon_entropy(prob_list: list[float]) -> float:
        """
        香农信息熵 H(X)
        
        H(X) = -Σp(xᵢ)log₂p(xᵢ)
        
        量化LLM输出不确定性、逻辑混乱度、幻觉发散程度
        
        Args:
            prob_list: 概率分布列表，所有元素应为[0,1]范围内
            
        Returns:
            float: 信息熵值，范围[0, +∞)
                   0表示确定性强（无混乱）
                   >0表示不确定性增加
            
        Example:
            >>> DeltaGUnified.shannon_entropy([0.5, 0.5])
            1.0
            >>> DeltaGUnified.shannon_entropy([1.0])
            0.0
        """
        entropy = 0.0
        for p in prob_list:
            if p < 0 or p > 1:
                logger.warning(f"概率值越界: {p}, 已截断至[0,1]")
                p = max(0.0, min(1.0, p))
            if p > 0:
                entropy -= p * math.log2(p)
        return round(entropy, 4)

    @staticmethod
    def shannon_channel_capacity(bandwidth: float, snr: float) -> float:
        """
        香农信道容量
        
        C = B * log₂(1 + S/N)
        
        定义记忆承载上限，压制噪声干扰
        
        Args:
            bandwidth: 信道带宽 B (Hz)
            snr: 信噪比 S/N
            
        Returns:
            float: 信道容量 (bps)
                   衡量信息通道的最大传输能力
            
        Example:
            >>> DeltaGUnified.shannon_channel_capacity(1000, 15)
            5804.0
        """
        if bandwidth < 0 or snr < 0:
            logger.error(f"参数不能为负: bandwidth={bandwidth}, snr={snr}")
            return 0.0
        return round(bandwidth * math.log2(1 + snr), 4)

    @staticmethod
    def code_redundancy(avg_len: float, entropy: float) -> float:
        """
        香农编码冗余度
        
        r = L_avg / H(X)
        
        约束代码/注释/MD必须达到无损编码标准
        
        Args:
            avg_len: 平均码长 L_avg
            entropy: 信息熵 H(X)
            
        Returns:
            float: 冗余度
                   =1 表示完美编码（无冗余）
                   >1 表示存在冗余
                   <1 不可能（违反香农第三定律）
            
        Note:
            根据香农无损编码定理: L_avg >= H(X)
            因此冗余度应 >= 1
        """
        if entropy == 0:
            return 0.0
        if avg_len < entropy:
            logger.warning(f"平均码长{avg_len}小于熵{entropy}，违反香农第三定律")
            return 1.0
        return round(avg_len / entropy, 4)

    # ==================== APEX ΔG 演化公式 ====================
    
    def calc_total_delta_g(
        self,
        H: float,           # 信息熵（香农）
        F: float,           # 保真度
        L: float,           # 逻辑链路
        N: float,           # 噪声水平
        C: float,           # 信道容量
        Omega: float,       # 技能覆盖率
        grad_E: float,      # 进化梯度
        Gamma: float,       # 编码标准率
        avg_code_len: float,# 平均代码长度
        Psi: float,         # 情感温度系数
        Theta: float        # 阈值稳定系数
    ) -> float:
        """
        终极全域融合ΔG总公式
        
        七大模块统一约束，防幻觉从根源做起
        
        ΔG = λ·H + λ·[(1-F) + e^(-τ·L) + δB] + λ·(N/C) 
           + λ·(1-Ω)·∇E + λ·(1-Γ)·r + λ·(1-Ψ)·τ + λ·(1-Θ)·H
        
        其中 r = code_redundancy(avg_code_len, H)
        
        Args:
            H: 信息熵 - LLM输出混乱度/幻觉倾向
            F: 保真度 - 输出与事实的吻合程度 [0,1]
            L: 逻辑链路 - 推理链完整性 [0,1]
            N: 噪声水平 - 干扰程度 [0,1]
            C: 信道容量 - 记忆承载上限
            Omega: 技能覆盖率 - 已覆盖技能占比 [0,1]
            grad_E: 进化梯度 - 自我进化速度 [0,1]
            Gamma: 编码标准率 - 遵循代码规范程度 [0,1]
            avg_code_len: 平均代码长度（字符数）
            Psi: 情感温度系数 - 对话拟人化程度 [0,1]
            Theta: 阈值稳定系数 - 系统稳定性 [0,1]
            
        Returns:
            float: ΔG总值
                   <= 2.10 → 健康稳态
                   2.10~4.0 → 轻度偏离（自动修复）
                   > 4.0 → 严重越界（触发自愈）
        """
        # 第一项：信息熵基础项
        term1 = self.LAMBDA * H
        
        # 第二项：保真度+链路+基础偏移
        term2 = self.LAMBDA * (1 - F) + math.exp(-self.TAU * L) + self.DELTA_B
        
        # 第三项：信噪比约束
        term3 = self.LAMBDA * (N / C if C != 0 else 1.0)
        
        # 第四项：进化驱动约束
        term4 = self.LAMBDA * (1 - Omega) * grad_E
        
        # 第五项：编码冗余约束
        red = self.code_redundancy(avg_code_len, H)
        term5 = self.LAMBDA * (1 - Gamma) * red
        
        # 第六项：情感温度约束
        term6 = self.LAMBDA * (1 - Psi) * self.TAU
        
        # 第七项：阈值稳定约束
        term7 = self.LAMBDA * (1 - Theta) * H
        
        # 汇总
        total = term1 + term2 + term3 + term4 + term5 + term6 + term7
        
        logger.info(f"ΔG计算: term1={term1:.4f}, term2={term2:.4f}, term3={term3:.4f}, "
                    f"term4={term4:.4f}, term5={term5:.4f}, term6={term6:.4f}, term7={term7:.4f}")
        logger.info(f"ΔG总分: {round(total, 4)}")
        
        return round(total, 4)

    def judge_system_state(self, dg_total: float) -> str:
        """
        系统稳态阈值判定
        
        三段式判定：健康/轻度偏离/严重越界
        
        Args:
            dg_total: ΔG总值
            
        Returns:
            str: 系统状态描述
                 "steady_健康稳态" - 无需干预
                 "mild_轻度偏离_自动局部修复" - 触发自动修复
                 "critical_严重越界_触发全量重启自愈" - 触发自愈流程
        """
        if dg_total <= 2.10:
            state = "steady_健康稳态"
            logger.info(f"系统状态: {state}")
        elif 2.10 < dg_total <= 4.0:
            state = "mild_轻度偏离_自动局部修复"
            logger.warning(f"系统状态: {state} - 启动自动修复")
        else:
            state = "critical_严重越界_触发全量重启自愈"
            logger.error(f"系统状态: {state} - 紧急自愈流程")
        
        return state


# ==================== 便捷函数接口 ====================

def quick_calc_delta_g(**kwargs) -> dict:
    """
    快速计算ΔG的便捷接口
    
    Usage:
        >>> result = quick_calc_delta_g(H=0.22, F=0.85, L=0.82, N=0.15, C=2.8,
        ...                                Omega=0.65, grad_E=0.90, Gamma=0.70,
        ...                                avg_code_len=48, Psi=0.78, Theta=0.82)
    """
    dg = DeltaGUnified()
    total = dg.calc_total_delta_g(**kwargs)
    state = dg.judge_system_state(total)
    return {"delta_g_total": total, "system_state": state}


def quick_calc(H: float, F: float, L: float, N: float = 0.0, C: float = 1.0,
               Omega: float = 1.0, grad_E: float = 0.0, Gamma: float = 1.0,
               avg_code_len: float = 1.0, Psi: float = 1.0, Theta: float = 1.0) -> tuple:
    """
    快速计算ΔG并返回状态判断（元组格式）
    
    Returns:
        tuple: (delta_g_total, system_state)
    
    Usage:
        >>> dg, state = quick_calc(H=2.0, F=0.9, L=100)
    """
    dg = DeltaGUnified()
    total = dg.calc_total_delta_g(H, F, L, N, C, Omega, grad_E, Gamma, avg_code_len, Psi, Theta)
    state = dg.judge_system_state(total)
    return total, state
