"""
emotion/emotion_hook.py - 情感钩子模块

自动拦截对话并注入情感温度
"""

import logging
from typing import Dict, Optional
from .emotion_core import EmotionCore

logger = logging.getLogger(__name__)


class EmotionHook:
    """
    情感钩子
    
    功能：
    1. 拦截用户输入检测语气
    2. 计算情感系数
    3. 注入温度到回复
    """
    
    def __init__(self):
        """初始化情感钩子"""
        self.core = EmotionCore()
        self.current_psi = self.core.PSI_BASE
        logger.info("情感钩子初始化完成")
    
    def init_emotion_system(self) -> bool:
        """
        初始化情感系统
        
        Returns:
            bool: 初始化是否成功
        """
        logger.info("情感系统初始化...")
        self.current_psi = self.core.PSI_BASE
        return True
    
    def process_input(self, user_input: str) -> Dict:
        """
        处理用户输入，检测语气
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            dict: {
                "original": str,
                "detected_tone": str,
                "psi": float
            }
        """
        detected_tone = self.core.detect_user_tone(user_input)
        psi = self.core.calc_psi(detected_tone)
        self.current_psi = psi
        
        return {
            "original": user_input,
            "detected_tone": detected_tone,
            "psi": psi
        }
    
    def process_output(self, response: str, psi: Optional[float] = None) -> str:
        """
        处理输出，注入情感温度
        
        Args:
            response: 原始回复
            psi: 指定情感系数（可选，使用当前值）
            
        Returns:
            str: 注入情感温度后的回复
        """
        if psi is None:
            psi = self.current_psi
        
        return self.core.inject_tone(response, psi)
    
    def full_process(self, user_input: str, response: str) -> Dict:
        """
        完整处理：输入检测 + 输出注入
        
        Args:
            user_input: 用户输入
            response: 原始回复
            
        Returns:
            dict: {
                "input_analysis": dict,
                "output": str,
                "psi": float
            }
        """
        input_analysis = self.process_input(user_input)
        output = self.process_output(response, input_analysis["psi"])
        
        return {
            "input_analysis": input_analysis,
            "output": output,
            "psi": input_analysis["psi"]
        }
