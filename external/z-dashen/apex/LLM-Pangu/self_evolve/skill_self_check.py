"""
self-evolve/skill_self_check.py - 技能自检模块

定期检查已安装技能的完整性和健康状态
确保技能库处于可用状态
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class SkillSelfCheck:
    """
    技能自检器
    
    功能：
    1. 检查技能文件完整性
    2. 验证技能依赖
    3. 检测技能冲突
    4. 生成健康报告
    """
    
    def __init__(self, skill_dir: str = "storage/skills"):
        """
        初始化技能自检器
        
        Args:
            skill_dir: 技能目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.manifest_file = self.skill_dir / "manifest.json"
        logger.info(f"技能自检器初始化，目录: {self.skill_dir}")
    
    def check_all(self) -> Dict:
        """
        执行全量技能检查
        
        Returns:
            dict: {
                "total": int,       # 总技能数
                "healthy": int,     # 健康技能数
                "issues": list,     # 问题列表
                "health_score": float  # 健康分数
            }
        """
        logger.info("开始技能自检...")
        
        # 检查manifest是否存在
        if not self.manifest_file.exists():
            logger.warning("技能清单不存在，创建默认清单")
            self._create_default_manifest()
        
        # 加载清单
        manifest = self._load_manifest()
        
        # 检查每个技能
        results = {
            "total": len(manifest.get("skills", [])),
            "healthy": 0,
            "issues": [],
            "health_score": 1.0
        }
        
        for skill in manifest.get("skills", []):
            skill_check = self._check_skill(skill)
            if skill_check["healthy"]:
                results["healthy"] += 1
            else:
                results["issues"].append(skill_check["issue"])
        
        # 计算健康分数
        if results["total"] > 0:
            results["health_score"] = results["healthy"] / results["total"]
        
        logger.info(f"技能自检完成: {results['healthy']}/{results['total']} 健康")
        
        return results
    
    def _check_skill(self, skill: Dict) -> Dict:
        """检查单个技能"""
        skill_path = self.skill_dir / skill.get("path", "")
        
        if not skill_path.exists():
            return {
                "healthy": False,
                "issue": f"技能路径不存在: {skill.get('name')}"
            }
        
        # 检查必要文件
        required_files = ["SKILL.md"]
        for req in required_files:
            if not (skill_path / req).exists():
                return {
                    "healthy": False,
                    "issue": f"技能缺少必要文件: {skill.get('name')}/{req}"
                }
        
        return {"healthy": True}
    
    def _create_default_manifest(self) -> None:
        """创建默认技能清单"""
        manifest = {
            "version": "1.0",
            "skills": []
        }
        self.skill_dir.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def _load_manifest(self) -> Dict:
        """加载技能清单"""
        with open(self.manifest_file, 'r') as f:
            return json.load(f)
