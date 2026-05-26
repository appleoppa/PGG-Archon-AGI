"""
auto-agent/self_inspect.py - 全局自检模块

定期执行系统级自检
监控各模块健康状态
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import datetime

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.delta_g_formula import DeltaGUnified


class SelfInspect:
    """
    全局自检器
    
    功能：
    1. 收集各模块状态
    2. 计算ΔG总值
    3. 判断系统健康
    """
    
    def __init__(self):
        """初始化全局自检器"""
        self.dg = DeltaGUnified()
        self.last_inspect_result: Optional[Dict] = None
        logger.info("全局自检器初始化完成")
    
    def full_inspect(self) -> Dict:
        """
        执行完整自检
        
        Returns:
            dict: {
                "delta_g_total": float,
                "system_state": str,
                "need_heal": bool,
                "need_fetch_skill": bool,
                "modules": dict,
                "timestamp": str
            }
        """
        logger.info("开始全局自检...")
        
        # 收集各模块参数（使用默认值/当前状态）
        H = 0.22        # 信息熵
        F = 0.85        # 保真度
        L = 0.82        # 逻辑链路
        N = 0.15        # 噪声水平
        C = 2.8         # 信道容量
        Omega = 0.65    # 技能覆盖率
        grad_E = 0.90   # 进化梯度
        Gamma = 0.70    # 编码标准率
        avg_code_len = 48  # 平均代码长度
        Psi = 0.78     # 情感温度系数
        Theta = 0.82   # 阈值稳定系数
        
        # 计算ΔG
        dg_total = self.dg.calc_total_delta_g(
            H, F, L, N, C, Omega, grad_E, Gamma, avg_code_len, Psi, Theta
        )
        
        # 判定状态
        state = self.dg.judge_system_state(dg_total)
        
        # 判断是否需要自愈
        need_heal = dg_total > 2.10
        
        # 判断是否需要拉取技能
        need_fetch_skill = Omega < 0.75
        
        result = {
            "delta_g_total": dg_total,
            "system_state": state,
            "need_heal": need_heal,
            "need_fetch_skill": need_fetch_skill,
            "modules": {
                "entropy": {"value": H, "status": "ok" if H < 0.5 else "warning"},
                "fidelity": {"value": F, "status": "ok" if F > 0.8 else "warning"},
                "logic": {"value": L, "status": "ok" if L > 0.7 else "warning"},
                "skill_coverage": {"value": Omega, "status": "ok" if Omega > 0.75 else "critical"}
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.last_inspect_result = result
        
        logger.info(f"全局自检完成: ΔG={dg_total}, 状态={state}")
        
        return result
    
    def quick_check(self) -> bool:
        """
        快速检查系统是否健康
        
        Returns:
            bool: 是否健康
        """
        if self.last_inspect_result is None:
            self.full_inspect()
        
        return self.last_inspect_result["system_state"].startswith("steady")
