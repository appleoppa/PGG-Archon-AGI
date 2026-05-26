"""
align/md_aligner.py - MD文档对齐模块

确保Markdown文档结构清晰、内容一致
减少文档相关的幻觉
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class MDAligner:
    """
    Markdown对齐器
    
    功能：
    1. 解析MD文档结构
    2. 检测语法错误
    3. 确保内容一致性
    """
    
    def __init__(self):
        """初始化MD对齐器"""
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
        self.code_block_pattern = re.compile(r'```[\s\S]*?```')
        logger.info("MD对齐器初始化完成")
    
    def align(self, md_content: str) -> Dict:
        """
        对齐MD文档
        
        Args:
            md_content: 原始MD内容
            
        Returns:
            dict: {
                "original": str,
                "aligned": str,
                "structure": dict,
                "issues": list,
                "score": float
            }
        """
        # 解析结构
        structure = self._parse_structure(md_content)
        
        # 检测问题
        issues = self._check_issues(md_content, structure)
        
        # 修复问题
        aligned = self._fix_issues(md_content, issues)
        
        # 计算质量分数
        score = self._calculate_score(structure, issues)
        
        logger.info(f"MD对齐完成: 问题数={len(issues)}, 质量分数={score:.2f}")
        
        return {
            "original": md_content,
            "aligned": aligned,
            "structure": structure,
            "issues": issues,
            "score": round(score, 4)
        }
    
    def _parse_structure(self, md_content: str) -> Dict:
        """解析MD文档结构"""
        headings = []
        links = []
        code_blocks = []
        
        for line_num, line in enumerate(md_content.split('\n'), 1):
            # 提取标题
            heading_match = self.heading_pattern.match(line)
            if heading_match:
                headings.append({
                    "level": len(heading_match.group(1)),
                    "text": heading_match.group(2),
                    "line": line_num
                })
            
            # 提取链接
            for match in self.link_pattern.finditer(line):
                links.append({
                    "text": match.group(1),
                    "url": match.group(2),
                    "line": line_num
                })
            
            # 提取代码块
            if '```' in line:
                code_blocks.append({"line": line_num})
        
        return {
            "headings": headings,
            "links": links,
            "code_blocks": code_blocks,
            "total_lines": len(md_content.split('\n'))
        }
    
    def _check_issues(self, md_content: str, structure: Dict) -> List[Dict]:
        """检测MD文档问题"""
        issues = []
        
        # 检查标题层级是否连续
        heading_levels = [h["level"] for h in structure["headings"]]
        for i in range(1, len(heading_levels)):
            if heading_levels[i] > heading_levels[i-1] + 1:
                issues.append({
                    "type": "heading_skip",
                    "severity": "warning",
                    "message": f"标题层级跳跃: {heading_levels[i-1]} → {heading_levels[i]}"
                })
        
        # 检查空链接
        for link in structure["links"]:
            if not link["url"] or link["url"] == "#":
                issues.append({
                    "type": "empty_link",
                    "severity": "error",
                    "message": f"空链接: '{link['text']}' 在第{link['line']}行"
                })
        
        return issues
    
    def _fix_issues(self, md_content: str, issues: List[Dict]) -> str:
        """修复检测到的问题"""
        # 目前仅标记问题，不自动修复
        # 后续可扩展自动修复逻辑
        return md_content
    
    def _calculate_score(self, structure: Dict, issues: List[Dict]) -> float:
        """计算文档质量分数"""
        base_score = 1.0
        
        # 错误扣分
        for issue in issues:
            if issue["severity"] == "error":
                base_score -= 0.2
            elif issue["severity"] == "warning":
                base_score -= 0.05
        
        return max(0.0, base_score)
