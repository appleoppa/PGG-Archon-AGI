"""
code-standard/standard_baseline.py - 规范基线模块

建立代码/注释/Markdown的规范标准
作为合规检查的基准
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class StandardBaseline:
    """
    规范基线管理器
    
    功能：
    1. 定义代码规范基线
    2. 管理规范版本
    3. 提供规范查询
    """
    
    def __init__(self):
        """初始化规范基线"""
        self.baseline_version = "1.0"
        self.baseline = self._create_baseline()
        logger.info(f"规范基线初始化完成，版本: {self.baseline_version}")
    
    def _create_baseline(self) -> Dict:
        """创建规范基线"""
        return {
            "version": self.baseline_version,
            "python": {
                "naming": {
                    "class": "PascalCase",
                    "function": "snake_case",
                    "variable": "snake_case",
                    "constant": "UPPER_SNAKE_CASE"
                },
                "docstring": {
                    "required": True,
                    "style": "Google",
                    "required_sections": ["Args", "Returns"]
                },
                "import": {
                    "order": ["stdlib", "third_party", "local"],
                    "relative": True
                }
            },
            "markdown": {
                "heading_style": "atx",
                "list_style": "asterisk",
                "max_heading_level": 6,
                "code_fence": "```"
            },
            "comment": {
                "inline_max_length": 80,
                "todo_format": "TODO: ",
                "fixme_format": "FIXME: "
            }
        }
    
    def get_baseline(self, language: str = "python") -> Dict:
        """
        获取指定语言的规范基线
        
        Args:
            language: 语言类型
            
        Returns:
            dict: 规范基线
        """
        return self.baseline.get(language, {})
    
    def validate_naming(self, name: str, entity_type: str) -> bool:
        """
        验证命名是否符合规范
        
        Args:
            name: 名称
            entity_type: 实体类型 (class/function/variable/constant)
            
        Returns:
            bool: 是否符合规范
        """
        standard = self.baseline["python"]["naming"].get(entity_type, "")
        
        if standard == "PascalCase":
            valid = name[0].isupper() and '_' not in name
        elif standard == "snake_case":
            valid = '_' in name or name.islower()
        elif standard == "UPPER_SNAKE_CASE":
            valid = name.isupper() and '_' in name
        else:
            valid = True
        
        if not valid:
            logger.warning(f"命名不符合{entity_type}规范: {name} (应为{standard})")
        
        return valid
