"""
core/constraint_engine.py - 盘古约束引擎

负责执行ΔG公式计算后的约束动作
将判定结果转化为具体的修复/自愈操作
"""

import logging
import os
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ConstraintEngine:
    """
    约束引擎
    
    根据ΔG判定结果，执行相应的约束动作
    - 健康稳态：放行
    - 轻度偏离：局部修复
    - 严重越界：全量自愈
    """
    
    def __init__(self):
        """初始化约束引擎"""
        self.repair_history: List[Dict] = []
        self._llm_config = self._load_llm_config()
        logger.info("约束引擎初始化完成")
    
    def _load_llm_config(self) -> Dict:
        """加载LLM配置"""
        config_file = "config/default_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载LLM配置失败: {e}")
        return {"llm": {"provider": "openai", "model": "gpt-4"}}
    
    def call_llm(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        调用真实LLM API
        
        支持 OpenAI / MiniMax / Ollama
        
        Args:
            prompt: 输入提示词
            context: 额外上下文
            
        Returns:
            str: LLM响应文本
        """
        context = context or {}
        provider = self._llm_config.get("llm", {}).get("provider", "openai")
        
        if provider == "openai":
            return self._call_openai(prompt, context)
        elif provider == "minimax":
            return self._call_minimax(prompt, context)
        elif provider == "ollama":
            return self._call_ollama(prompt, context)
        else:
            logger.warning(f"未知LLM provider: {provider}")
            return self._call_ollama(prompt, context)
    
    def _call_openai(self, prompt: str, context: Dict) -> str:
        """调用OpenAI API"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY未设置，尝试降级到Ollama")
            return self._call_ollama(prompt, context)
        
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            model = self._llm_config.get("llm", {}).get("model", "gpt-4")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是盘古框架的约束引擎，负责分析系统状态并提供修复建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            return f"[OpenAI调用失败: {e}]"
    
    def _call_minimax(self, prompt: str, context: Dict) -> str:
        """调用MiniMax API"""
        api_key = os.environ.get("MINIMAX_API_KEY")
        group_id = os.environ.get("MINIMAX_GROUP_ID")
        if not api_key or not group_id:
            logger.warning("MiniMax凭证未设置，尝试降级到Ollama")
            return self._call_ollama(prompt, context)
        
        try:
            import requests
            url = f"https://api.minimax.chat/v1/text/chatcompletion_pro?GroupId={group_id}"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "abab6.5s-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 512
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("messages", [{}])[0].get("text", "")
            else:
                logger.error(f"MiniMax API错误: {resp.status_code} {resp.text}")
                return f"[MiniMax调用失败: {resp.status_code}]"
        except Exception as e:
            logger.error(f"MiniMax API调用异常: {e}")
            return f"[MiniMax调用异常: {e}]"
    
    def _call_ollama(self, prompt: str, context: Dict) -> str:
        """调用本地Ollama API"""
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model = self._llm_config.get("llm", {}).get("model", "deepseek-coder")
        
        try:
            import requests
            url = f"{host}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 512}
            }
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            else:
                logger.error(f"Ollama API错误: {resp.status_code}")
                return f"[Ollama调用失败: {resp.status_code}]"
        except Exception as e:
            logger.error(f"Ollama API调用异常: {e}")
            return f"[Ollama调用失败: {e}]"
    
    def apply_constraints(self, dg_total: float, context: Optional[Dict] = None) -> Dict:
        """
        根据ΔG总值应用约束策略
        
        Args:
            dg_total: ΔG计算总值
            context: 额外上下文信息
            
        Returns:
            dict: {
                "action": str,      # 执行的动作
                "details": dict,    # 动作详情
                "success": bool     # 是否成功
            }
        """
        context = context or {}
        
        if dg_total <= 2.10:
            action = self._allow()
        elif 2.10 < dg_total <= 4.0:
            action = self._partial_repair(context)
        else:
            action = self._full_heal(context)
        
        self.repair_history.append({
            "dg_total": dg_total,
            "action": action,
            "context": context
        })
        
        return action
    
    def _allow(self) -> Dict:
        """健康稳态 - 放行"""
        logger.info("ΔG处于健康范围，放行请求")
        return {
            "action": "allow",
            "details": {"message": "系统稳态，放行"},
            "success": True
        }
    
    def _partial_repair(self, context: Dict) -> Dict:
        """轻度偏离 - 局部修复"""
        logger.warning("ΔG轻度偏离，启动局部修复")
        repair_type = context.get("repair_type", "default")
        
        # 调用LLM获取修复建议
        llm_suggestion = ""
        if self._llm_config.get("llm", {}).get("enabled", True):
            prompt = f"系统ΔG轻度偏离，当前值={context.get('dg_total', 'unknown')}，请提供修复建议（简短）。"
            try:
                llm_suggestion = self.call_llm(prompt, context)
            except Exception as e:
                logger.warning(f"LLM修复建议获取失败: {e}")
        
        return {
            "action": "partial_repair",
            "details": {
                "repair_type": repair_type,
                "message": "局部修复已完成",
                "llm_suggestion": llm_suggestion
            },
            "success": True
        }
    
    def _full_heal(self, context: Dict) -> Dict:
        """严重越界 - 全量自愈"""
        logger.error("ΔG严重越界，启动全量自愈")
        
        # 调用LLM获取严重越界分析
        llm_analysis = ""
        if self._llm_config.get("llm", {}).get("enabled", True):
            prompt = f"系统ΔG严重越界，当前值={context.get('dg_total', 'unknown')}，请分析根本原因并提供修复步骤（简洁）。"
            try:
                llm_analysis = self.call_llm(prompt, context)
            except Exception as e:
                logger.warning(f"LLM分析获取失败: {e}")
        
        return {
            "action": "full_heal",
            "details": {
                "message": "全量自愈已触发",
                "recovery_steps": ["状态重置", "基因修复", "记忆恢复"],
                "llm_analysis": llm_analysis
            },
            "success": True
        }
