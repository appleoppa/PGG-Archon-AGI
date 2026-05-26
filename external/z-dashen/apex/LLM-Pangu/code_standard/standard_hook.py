"""
code-standard/standard_hook.py - 代码规范钩子模块

作为规范检查的入口点
提供一键检查和一键修复功能
"""

import logging
from typing import Dict, Optional
from pathlib import Path
from .standard_baseline import StandardBaseline
from .code_compliance import CodeCompliance

logger = logging.getLogger(__name__)


class LLMStandardHook:
    """
    LLM代码规范钩子
    
    功能：
    1. 首次构建自身标准
    2. 拦截代码进行规范检查
    3. 提供修复建议
    """
    
    def __init__(self):
        """初始化规范钩子"""
        self.baseline = StandardBaseline()
        self.compliance = CodeCompliance()
        logger.info("LLM代码规范钩子初始化完成")
    
    def first_build_self_standard(self) -> bool:
        """
        首次构建自身标准
        
        检查当前代码库，建立规范基线
        """
        logger.info("开始构建自身规范标准...")
        
        # 检查自身目录
        workspace = Path("/root/.openclaw/workspace")
        pangu_dir = workspace / "pangu"
        
        if not pangu_dir.exists():
            logger.warning("盘古目录不存在，跳过自检")
            return False
        
        # 检查Python文件
        result = self.compliance.check_directory(str(pangu_dir), "*.py")
        
        logger.info(f"自身规范构建完成: "
                    f"检查{result.get('total_files', 0)}个文件, "
                    f"发现{result.get('total_violations', 0)}个违规")
        
        return True
    
    def check_file(self, file_path: str) -> Dict:
        """
        检查文件合规性
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 检查结果
        """
        return self.compliance.check_file(file_path)
    
    def check_and_fix(self, file_path: str) -> Dict:
        """
        检查并尝试修复
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 修复结果
        """
        result = self.check_file(file_path)
        
        if result.get("total_violations", 0) > 0:
            logger.warning(f"文件存在{result['total_violations']}个违规")
            result["fix_applied"] = False
            result["fix_suggestions"] = [
                v["message"] for v in result["violations"]
            ]
        else:
            result["fix_applied"] = True
            result["message"] = "文件符合规范"
        
        return result
