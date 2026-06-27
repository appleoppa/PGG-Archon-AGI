"""
memory/memory_persist.py - 记忆持久化模块

负责记忆的持久化存储和恢复
确保隔夜/重启后记忆不丢失
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryPersist:
    """
    记忆持久化管理器
    
    功能：
    1. 将记忆写入磁盘（JSON格式）
    2. 从磁盘恢复记忆
    3. 自动备份与清理
    """
    
    def __init__(self, storage_dir: str = "storage"):
        """
        初始化记忆持久化管理器
        
        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_dir / "pangu_memory.json"
        self.backup_dir = self.storage_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"记忆持久化管理器初始化，存储目录: {self.storage_dir}")
    
    def save(self, memory_data: Dict[str, Any], auto_backup: bool = True) -> bool:
        """
        保存记忆到磁盘
        
        Args:
            memory_data: 记忆数据字典
            auto_backup: 是否自动备份
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 读取现有记忆
            existing = self._read_existing()
            
            # 合并记忆（保留历史）
            merged = self._merge_memory(existing, memory_data)
            
            # 添加时间戳
            merged["_meta"] = {
                "last_updated": datetime.now().isoformat(),
                "version": merged.get("_meta", {}).get("version", 1) + 1
            }
            
            # 写入主文件
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            
            # 备份
            if auto_backup:
                self._create_backup(merged)
            
            logger.info(f"记忆已保存，共 {len(merged)} 个键")
            return True
            
        except Exception as e:
            logger.error(f"记忆保存失败: {e}")
            return False
    
    def load(self) -> Dict[str, Any]:
        """
        从磁盘加载记忆
        
        Returns:
            dict: 记忆数据
        """
        try:
            memory_data = self._read_existing()
            logger.info(f"记忆已加载，共 {len(memory_data)} 个键")
            return memory_data
        except Exception as e:
            logger.error(f"记忆加载失败: {e}")
            return {}
    
    def clear(self) -> bool:
        """清空所有记忆"""
        try:
            if self.memory_file.exists():
                self.memory_file.unlink()
            logger.info("记忆已清空")
            return True
        except Exception as e:
            logger.error(f"记忆清空失败: {e}")
            return False
    
    def _read_existing(self) -> Dict[str, Any]:
        """读取现有记忆文件"""
        if not self.memory_file.exists():
            return {}
        
        with open(self.memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _merge_memory(self, existing: Dict, new: Dict) -> Dict:
        """合并新旧记忆"""
        merged = existing.copy()
        merged.update(new)
        return merged
    
    def _create_backup(self, data: Dict) -> None:
        """创建备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"pangu_memory_{timestamp}.json"
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"备份已创建: {backup_file}")
        
        # 清理旧备份（保留最近10个）
        self._cleanup_old_backups()
    
    def _cleanup_old_backups(self) -> None:
        """清理旧备份文件"""
        backups = sorted(self.backup_dir.glob("pangu_memory_*.json"))
        if len(backups) > 10:
            for old in backups[:-10]:
                old.unlink()
                logger.debug(f"旧备份已删除: {old}")
