"""
auto-agent/agent_hook.py - Agent钩子模块

整合所有主动智能体能力
提供统一的入口和调度
"""

import logging
from typing import Dict, Optional
from .self_inspect import SelfInspect
from .self_heal import SelfHeal
from .github_auto_fetch import GitHubAutoFetch

logger = logging.getLogger(__name__)


class AutoAgentHook:
    """
    自动智能体钩子
    
    整合：
    1. 全局自检 (SelfInspect)
    2. 主动自愈 (SelfHeal)
    3. GitHub补能 (GitHubAutoFetch)
    """
    
    def __init__(self):
        """初始化Agent钩子"""
        self.inspector = SelfInspect()
        self.healer = SelfHeal(self.inspector)
        self.fetcher = GitHubAutoFetch()
        self.enabled = True
        logger.info("Agent钩子初始化完成")
    
    def run_auto_agent(self) -> Dict:
        """
        运行自动智能体
        
        执行完整流程：
        1. 自检
        2. 判断是否自愈
        3. 判断是否补能
        
        Returns:
            dict: 运行结果
        """
        if not self.enabled:
            logger.info("自动智能体已禁用")
            return {"enabled": False}
        
        logger.info("启动自动智能体...")
        
        # 1. 全局自检
        inspect_result = self.inspector.full_inspect()
        
        # 2. 自愈判断
        heal_result = None
        if inspect_result["need_heal"]:
            heal_result = self.healer.auto_heal_if_needed(
                inspect_result["delta_g_total"]
            )
        
        # 3. 技能补能判断
        fetch_result = None
        if inspect_result["need_fetch_skill"]:
            fetch_result = self.fetcher.auto_fetch("skills")
        
        result = {
            "enabled": True,
            "inspect": inspect_result,
            "heal": heal_result,
            "fetch": fetch_result,
            "status": "healthy" if not inspect_result["need_heal"] else "healing"
        }
        
        logger.info(f"自动智能体运行完成: status={result['status']}")
        
        return result
    
    def trigger_heal(self, issue: Dict) -> Dict:
        """
        手动触发自愈
        
        Args:
            issue: 问题描述
            
        Returns:
            dict: 自愈结果
        """
        return self.healer.heal(issue)
    
    def trigger_fetch(self, capability: str) -> Dict:
        """
        手动触发拉取
        
        Args:
            capability: 能力名称
            
        Returns:
            dict: 拉取结果
        """
        return self.fetcher.auto_fetch(capability)
