"""
align/prompt_aligner.py - Prompt对齐模块

确保用户Prompt与系统理解一致
减少因Prompt歧义导致的幻觉
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptAligner:
    """
    Prompt对齐器
    
    功能：
    1. 解析用户Prompt意图
    2. 检测歧义和模糊表达
    3. 生成对齐后的清晰Prompt
    """
    
    def __init__(self):
        """初始化Prompt对齐器"""
        self.ambiguous_patterns = [
            "可能", "也许", "大概", "应该", "或许",
            "好像", "似乎", "估计", "说不定"
        ]
        self.intent_keywords = {
            "code": ["代码", "程序", "函数", "实现", "写", "code", "function"],
            "question": ["什么", "为什么", "怎么", "如何", "who", "what", "why", "how"],
            "analysis": ["分析", "比较", "评估", "analyze", "compare", "evaluate"],
            "create": ["创建", "生成", "新建", "create", "generate", "new"]
        }
        logger.info("Prompt对齐器初始化完成")
    
    def align(self, prompt: str, context: Optional[Dict] = None) -> Dict:
        """
        对齐用户Prompt
        
        Args:
            prompt: 原始用户Prompt
            context: 上下文信息
            
        Returns:
            dict: {
                "original": str,    # 原始Prompt
                "aligned": str,    # 对齐后Prompt
                "intent": str,     # 识别出的意图
                "ambiguities": list,  # 检测到的歧义
                "confidence": float   # 对齐置信度
            }
        """
        context = context or {}
        
        # 检测歧义
        ambiguities = self._detect_ambiguities(prompt)
        
        # 识别意图
        intent = self._recognize_intent(prompt)
        
        # 生成对齐Prompt
        aligned = self._build_aligned_prompt(prompt, ambiguities)
        
        # 计算置信度
        confidence = 1.0 - (len(ambiguities) * 0.15)
        
        logger.info(f"Prompt对齐完成: 意图={intent}, 歧义数={len(ambiguities)}, 置信度={confidence:.2f}")
        
        return {
            "original": prompt,
            "aligned": aligned,
            "intent": intent,
            "ambiguities": ambiguities,
            "confidence": round(confidence, 4)
        }
    
    def _detect_ambiguities(self, prompt: str) -> List[str]:
        """检测Prompt中的歧义表达"""
        found = []
        for pattern in self.ambiguous_patterns:
            if pattern in prompt:
                found.append(pattern)
        return found
    
    def _recognize_intent(self, prompt: str) -> str:
        """识别Prompt意图"""
        prompt_lower = prompt.lower()
        for intent, keywords in self.intent_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return intent
        return "general"
    
    def _build_aligned_prompt(self, prompt: str, ambiguities: List[str]) -> str:
        """构建对齐后的Prompt"""
        if not ambiguities:
            return prompt
        
        # 保留原始意图，添加澄清要求
        aligned = prompt + "\n[注意：请明确表达，避免歧义]"
        return aligned
