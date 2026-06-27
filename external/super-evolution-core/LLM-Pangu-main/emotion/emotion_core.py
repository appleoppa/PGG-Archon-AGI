"""
emotion/emotion_core.py - 情感温度核心模块

为对话注入拟人化情感温度
脱离机械冰冷的回复风格
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EmotionCore:
    """
    情感温度核心
    
    功能：
    1. 计算情感系数Ψ
    2. 识别用户语气
    3. 注入情感温度
    """
    
    def __init__(self):
        """初始化情感温度核心"""
        self.PSI_BASE = 0.75      # 基准情感系数
        self.PSI_WARM = 0.88     # 温暖语气系数
        self.PSI_COLD = 0.62     # 冷淡语气系数
        
        # 软化词库
        self.soft_words = [
            "理解", "没关系", "我帮你梳理", "我明白你的意思",
            "我们一起来解决", "好的", "没问题", "别担心",
            "明白了", "了解了", "完全懂你", "为你服务"
        ]
        
        # 温暖前缀
        self.warm_prefixes = [
            "😊 我理解你的需求，",
            "😊 没问题，",
            "😊 明白了，我来帮你，",
            "🤗 别着急，"
        ]
        
        # 冷淡前缀（用于纠正错误）
        self.cold_prefixes = [
            "📌 收到指令，",
            "⚠️ 注意，",
            "🔧 正在处理，"
        ]
        
        logger.info("情感温度核心初始化完成")
    
    def calc_psi(self, user_tone: str = "normal") -> float:
        """
        动态计算情感系数Ψ
        
        Args:
            user_tone: 用户语气 (warm/normal/cold)
            
        Returns:
            float: 情感系数Ψ，范围[0,1]
        """
        if user_tone == "warm":
            psi = self.PSI_WARM
        elif user_tone == "cold":
            psi = self.PSI_COLD
        else:
            psi = self.PSI_BASE
        
        logger.debug(f"情感系数计算: user_tone={user_tone}, psi={psi}")
        return psi
    
    def detect_user_tone(self, text: str) -> str:
        """
        检测用户语气
        
        Args:
            text: 用户输入文本
            
        Returns:
            str: 语气类型 (warm/normal/cold)
        """
        text_lower = text.lower()
        
        # 温暖语气关键词
        warm_keywords = ["谢谢", "好", "棒", "厉害", "喜欢", "赞", "感谢"]
        for kw in warm_keywords:
            if kw in text_lower:
                return "warm"
        
        # 冷淡语气关键词
        cold_keywords = ["不对", "错", "不行", "不是", "不满意", "投诉"]
        for kw in cold_keywords:
            if kw in text_lower:
                return "cold"
        
        return "normal"
    
    def inject_tone(self, resp_text: str, psi: float) -> str:
        """
        给回复注入温度语气
        
        Args:
            resp_text: 原始回复文本
            resp_text: 情感系数
            
        Returns:
            str: 注入情感温度后的回复
        """
        if psi >= 0.8:
            # 温暖语气
            import random
            prefix = random.choice(self.warm_prefixes)
            resp_text = prefix + resp_text
        elif psi <= 0.65:
            # 冷淡语气（更正式）
            import random
            prefix = random.choice(self.cold_prefixes)
            resp_text = prefix + resp_text
        
        return resp_text
    
    def add_soft_words(self, text: str, ratio: float = 0.3) -> str:
        """
        按比例在回复中插入软化词
        
        Args:
            text: 原始文本
            ratio: 插入比例 (0~1)
            
        Returns:
            str: 添加软化词后的文本
        """
        import random
        
        words = text.split()
        if len(words) < 3:
            return text
        
        insert_count = max(1, int(len(words) * ratio))
        insert_positions = random.sample(range(1, len(words)), min(insert_count, len(words)-1))
        
        for pos in sorted(insert_positions):
            words.insert(pos, random.choice(self.soft_words))
        
        return ' '.join(words)
