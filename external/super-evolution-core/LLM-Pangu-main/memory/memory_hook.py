"""
memory/memory_hook.py - 记忆钩子模块

自动拦截并管理对话记忆
实现隔夜/重启记忆不丢失
"""

import logging
from typing import Dict, List, Optional
from .memory_persist import MemoryPersist

logger = logging.getLogger(__name__)


class LLMMemoryHook:
    """
    LLM记忆钩子
    
    功能：
    1. 自动保存对话记忆
    2. 自动恢复历史记忆
    3. 管理短时/长时记忆分层
    """
    
    def __init__(self):
        """初始化记忆钩子"""
        self.persist = MemoryPersist()
        self.short_term: List[Dict] = []
        self.long_term: Dict = {}
        self.session_id: Optional[str] = None
        logger.info("LLM记忆钩子初始化完成")
    
    def start_session(self, session_id: str) -> None:
        """
        开始新会话
        
        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        logger.info(f"会话开始: {session_id}")
        
        # 尝试恢复历史记忆
        self.auto_restore_all()
    
    def add_exchange(self, user_input: str, assistant_response: str) -> None:
        """
        添加对话交换记录
        
        Args:
            user_input: 用户输入
            assistant_response: 助手回复
        """
        exchange = {
            "session_id": self.session_id,
            "user": user_input,
            "assistant": assistant_response
        }
        self.short_term.append(exchange)
        
        # 定期持久化
        if len(self.short_term) >= 10:
            self._persist_short_term()
        
        logger.debug(f"对话已记录，当前短时记忆: {len(self.short_term)}条")
    
    def auto_restore_all(self) -> bool:
        """
        自动恢复所有记忆
        
        从持久化存储中恢复长时记忆和最近的对话
        """
        logger.info("开始自动恢复记忆...")
        
        try:
            # 加载持久化数据
            data = self.persist.load()
            
            # 恢复长时记忆
            self.long_term = data.get("long_term", {})
            
            # 恢复最近的短时记忆
            self.short_term = data.get("short_term", [])
            
            logger.info(f"记忆恢复完成: 长时{len(self.long_term)}个键, 短时{len(self.short_term)}条")
            return True
            
        except Exception as e:
            logger.error(f"记忆恢复失败: {e}")
            return False
    
    def persist_all(self) -> bool:
        """
        持久化所有记忆
        
        将当前所有记忆写入磁盘
        """
        data = {
            "long_term": self.long_term,
            "short_term": self.short_term
        }
        return self.persist.save(data)
    
    def _persist_short_term(self) -> None:
        """持久化短时记忆"""
        data = {
            "long_term": self.long_term,
            "short_term": self.short_term
        }
        self.persist.save(data)
        logger.info("短时记忆已持久化")
    
    def get_context(self, max_turns: int = 10) -> List[Dict]:
        """
        获取对话上下文
        
        Args:
            max_turns: 最大返回轮数
            
        Returns:
            list: 最近的对话记录
        """
        return self.short_term[-max_turns:]
    
    def clear_session(self) -> None:
        """清理当前会话记忆（可选）"""
        # 可选择是否清空
        # self.short_term = []
        logger.info("会话记忆已标记清理")
