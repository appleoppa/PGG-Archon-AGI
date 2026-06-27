"""
code-standard/code_compliance.py - 代码合规检查模块

检查代码是否符合规范基线
生成合规报告
"""

import re
import logging
from typing import Dict, List, Tuple
from pathlib import Path
from .standard_baseline import StandardBaseline

logger = logging.getLogger(__name__)


class CodeCompliance:
    """
    代码合规检查器
    
    功能：
    1. 解析代码结构
    2. 检查命名规范
    3. 检查文档字符串
    4. 生成合规报告
    """
    
    def __init__(self):
        """初始化合规检查器"""
        self.baseline = StandardBaseline()
        self.violations: List[Dict] = []
        logger.info("代码合规检查器初始化完成")
    
    def check_file(self, file_path: str) -> Dict:
        """
        检查单个文件的合规性
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: {
                "file": str,
                "total_violations": int,
                "violations": list,
                "compliance_rate": float
            }
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                "file": file_path,
                "error": "文件不存在"
            }
        
        content = path.read_text(encoding='utf-8')
        suffix = path.suffix
        
        self.violations = []
        
        if suffix == '.py':
            self._check_python(content)
        elif suffix in ['.md', '.markdown']:
            self._check_markdown(content)
        
        compliance_rate = 1.0 - (len(self.violations) * 0.05)
        
        return {
            "file": file_path,
            "total_violations": len(self.violations),
            "violations": self.violations,
            "compliance_rate": max(0.0, compliance_rate)
        }
    
    def _check_python(self, content: str) -> None:
        """检查Python代码"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 检查单行长度
            if len(line) > 120:
                self.violations.append({
                    "line": i,
                    "type": "line_too_long",
                    "message": f"行长度{len(line)}超过120字符"
                })
            
            # 检查docstring（简单检查）
            if line.strip().startswith('def ') or line.strip().startswith('class '):
                # 检查后续是否有docstring
                next_lines = '\n'.join(lines[i:min(i+5, len(lines))])
                if '"""' not in next_lines and "'''" not in next_lines:
                    self.violations.append({
                        "line": i,
                        "type": "missing_docstring",
                        "message": f"缺少docstring: {line.strip()[:50]}"
                    })
    
    def _check_markdown(self, content: str) -> None:
        """检查Markdown文档"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 检查标题层级
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                if level > 6:
                    self.violations.append({
                        "line": i,
                        "type": "heading_too_deep",
                        "message": f"标题层级{level}超过6级"
                    })
            
            # 检查链接格式
            if '](' in line and not re.search(r'\[.+\]\(.+\)', line):
                self.violations.append({
                    "line": i,
                    "type": "malformed_link",
                    "message": "链接格式不规范"
                })
    
    def check_directory(self, dir_path: str, pattern: str = "*.py") -> Dict:
        """
        检查目录下所有匹配的文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            dict: 汇总报告
        """
        path = Path(dir_path)
        results = []
        
        for file_path in path.rglob(pattern):
            result = self.check_file(str(file_path))
            results.append(result)
        
        total_violations = sum(r.get("total_violations", 0) for r in results)
        avg_compliance = sum(r.get("compliance_rate", 0) for r in results) / len(results) if results else 1.0
        
        return {
            "directory": dir_path,
            "total_files": len(results),
            "total_violations": total_violations,
            "average_compliance": round(avg_compliance, 4),
            "files": results
        }
