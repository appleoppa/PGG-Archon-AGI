"""
auto-agent/github_auto_fetch.py - GitHub自动拉取模块

自动检测缺失能力并从GitHub拉取补充
"""

import logging
import subprocess
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GitHubAutoFetch:
    """
    GitHub自动拉取器
    
    功能：
    1. 监控缺失能力
    2. 从GitHub搜索相关项目
    3. 自动克隆安装
    """
    
    def __init__(self, token: str = None, repo: str = None):
        """初始化GitHub自动拉取器"""
        self.token = token
        self.repo = repo
        self.known_repos = {
            "skills": "https://github.com/ApexSpiral/skills.git",
            "pangu": "https://github.com/ApexSpiral/LLM-Pangu.git",
            "evolver": "https://github.com/ApexSpiral/evolver.git"
        }
        self.fetch_history: List[Dict] = []
        logger.info("GitHub自动拉取器初始化完成")
    
    def auto_fetch(self, capability: str) -> Dict:
        """
        自动拉取能力
        
        Args:
            capability: 能力名称
            
        Returns:
            dict: {
                "success": bool,
                "repo": str,
                "path": str
            }
        """
        logger.info(f"自动拉取能力: {capability}")
        
        if capability in self.known_repos:
            repo_url = self.known_repos[capability]
            return self._clone_repo(repo_url, capability)
        else:
            logger.warning(f"未知能力: {capability}")
            return {
                "success": False,
                "error": f"未知能力: {capability}"
            }
    
    def _clone_repo(self, repo_url: str, name: str) -> Dict:
        """
        真实克隆GitHub仓库
        
        Args:
            repo_url: 仓库URL
            name: 名称
            
        Returns:
            dict: 克隆结果
        """
        logger.info(f"克隆仓库: {repo_url}")
        
        target_dir = f"storage/github_skills/{name}"
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, target_dir],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                logger.info(f"克隆成功: {target_dir}")
                self.fetch_history.append({
                    "repo": repo_url,
                    "name": name,
                    "path": target_dir,
                    "success": True
                })
                return {"success": True, "repo": repo_url, "path": target_dir}
            else:
                logger.error(f"克隆失败: {result.stderr}")
                return {"success": False, "error": result.stderr}
        except subprocess.TimeoutExpired:
            logger.error("克隆超时（60秒）")
            return {"success": False, "error": "Clone timeout (60s)"}
        except Exception as e:
            logger.error(f"克隆异常: {e}")
            return {"success": False, "error": str(e)}
    
    def search_and_fetch(self, query: str) -> List[Dict]:
        """
        搜索并拉取
        
        Args:
            query: 搜索关键词
            
        Returns:
            list: 匹配结果
        """
        logger.info(f"搜索GitHub: {query}")
        
        # 实际实现应调用GitHub API
        # 这里简化处理
        return []
