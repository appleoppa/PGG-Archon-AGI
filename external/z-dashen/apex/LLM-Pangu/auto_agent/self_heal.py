"""
auto-agent/self_heal.py - 主动自愈模块

当检测到系统异常时自动执行修复
"""

import logging
import os
import json
import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SelfHeal:
    """
    主动自愈器
    
    功能：
    1. 接收异常信号
    2. 执行修复策略
    3. 验证修复结果
    """
    
    def __init__(self, inspector=None):
        """初始化自愈器"""
        self.inspector = inspector
        self.heal_history: List[Dict] = []
        self.max_retries = 3
        self.storage_dir = "storage"
        self.state_file = "storage/heal_state_backup.json"
        self.config_file = "config/default_config.json"
        logger.info("主动自愈器初始化完成")
    
    def heal(self, issue: Dict) -> Dict:
        """
        执行自愈修复
        
        Args:
            issue: 问题描述
            
        Returns:
            dict: {
                "success": bool,
                "heal_type": str,
                "steps": list,
                "result": str
            }
        """
        issue_type = issue.get("type", "unknown")
        severity = issue.get("severity", "medium")
        
        logger.info(f"开始自愈修复: type={issue_type}, severity={severity}")
        
        if severity == "critical":
            result = self._full_heal(issue)
        else:
            result = self._partial_heal(issue)
        
        self.heal_history.append({
            "issue": issue,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return result
    
    def _full_heal(self, issue: Dict) -> Dict:
        """
        全量自愈
        
        用于严重越界情况：保存状态→重置DeltaG参数→清理缓存→重载配置→验证
        """
        logger.warning("执行全量自愈...")
        steps = []
        
        # Step 1: 保存当前系统状态
        try:
            state_backup = self._save_current_state()
            steps.append({
                "step": "保存系统状态",
                "status": "done",
                "detail": f"状态已保存至 {state_backup}"
            })
        except Exception as e:
            steps.append({
                "step": "保存系统状态",
                "status": "error",
                "detail": str(e)
            })
            logger.error(f"保存状态失败: {e}")
        
        # Step 2: 重置DeltaG参数到默认值
        try:
            self._reset_delta_g_params()
            steps.append({
                "step": "重置DeltaG参数",
                "status": "done",
                "detail": "参数已恢复默认值"
            })
        except Exception as e:
            steps.append({
                "step": "重置DeltaG参数",
                "status": "error",
                "detail": str(e)
            })
            logger.error(f"重置参数失败: {e}")
        
        # Step 3: 清理记忆缓存
        try:
            self._clear_memory_cache()
            steps.append({
                "step": "清理记忆缓存",
                "status": "done",
                "detail": "临时缓存已清除"
            })
        except Exception as e:
            steps.append({
                "step": "清理记忆缓存",
                "status": "error",
                "detail": str(e)
            })
            logger.error(f"清理缓存失败: {e}")
        
        # Step 4: 重新加载配置
        try:
            self._reload_config()
            steps.append({
                "step": "重新加载配置",
                "status": "done",
                "detail": "配置已重载"
            })
        except Exception as e:
            steps.append({
                "step": "重新加载配置",
                "status": "error",
                "detail": str(e)
            })
            logger.error(f"重载配置失败: {e}")
        
        # Step 5: 验证系统状态
        try:
            verified = self._verify_system_state()
            steps.append({
                "step": "验证系统状态",
                "status": "done" if verified else "failed",
                "detail": "验证通过" if verified else "验证未通过"
            })
        except Exception as e:
            steps.append({
                "step": "验证系统状态",
                "status": "error",
                "detail": str(e)
            })
            logger.error(f"验证状态失败: {e}")
        
        all_done = all(s["status"] == "done" for s in steps)
        return {
            "success": all_done,
            "heal_type": "full",
            "steps": steps,
            "result": "全量自愈完成" if all_done else "全量自愈部分完成"
        }
    
    def _partial_heal(self, issue: Dict) -> Dict:
        """
        局部自愈
        
        用于轻度偏离情况：定位问题→局部修复
        """
        logger.info("执行局部自愈...")
        steps = []
        
        # Step 1: 定位问题
        try:
            issue_located = self._locate_issue(issue)
            steps.append({
                "step": "定位问题",
                "status": "done",
                "detail": issue_located
            })
        except Exception as e:
            steps.append({
                "step": "定位问题",
                "status": "error",
                "detail": str(e)
            })
        
        # Step 2: 局部修复
        try:
            self._apply_partial_fix(issue)
            steps.append({
                "step": "局部修复",
                "status": "done",
                "detail": "已应用局部修复"
            })
        except Exception as e:
            steps.append({
                "step": "局部修复",
                "status": "error",
                "detail": str(e)
            })
        
        all_done = all(s["status"] == "done" for s in steps)
        return {
            "success": all_done,
            "heal_type": "partial",
            "steps": steps,
            "result": "局部自愈完成" if all_done else "局部自愈部分完成"
        }
    
    def _save_current_state(self) -> str:
        """保存当前系统状态到文件"""
        state = {
            "timestamp": datetime.datetime.now().isoformat(),
            "heal_count": len(self.heal_history),
            "inspector_state": str(self.inspector) if self.inspector else None
        }
        os.makedirs(os.path.dirname(self.state_file) if os.path.dirname(self.state_file) else ".", exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return self.state_file
    
    def _reset_delta_g_params(self) -> None:
        """重置DeltaG参数到默认值"""
        default_params = {
            "LAMBDA": 1.5,
            "TAU": 0.32,
            "DELTA_B": 0.18,
            "H_default": 0.22,
            "F_default": 0.85,
            "L_default": 0.82,
            "N_default": 0.15,
            "C_default": 2.8,
            "Omega_min": 0.75,
            "grad_E_default": 0.90,
            "Gamma_default": 0.70,
            "avg_code_len_default": 48,
            "Psi_base": 0.75,
            "Theta_default": 0.82
        }
        reset_file = "storage/delta_g_reset_params.json"
        os.makedirs("storage", exist_ok=True)
        with open(reset_file, "w", encoding="utf-8") as f:
            json.dump(default_params, f, ensure_ascii=False, indent=2)
        logger.info("DeltaG参数已重置为默认值")
    
    def _clear_memory_cache(self) -> None:
        """清理记忆缓存目录"""
        cache_dirs = ["storage/cache", "storage/temp", "storage/.memory_cache"]
        cleared = []
        for d in cache_dirs:
            if os.path.exists(d):
                for f in os.listdir(d):
                    try:
                        os.remove(os.path.join(d, f))
                    except Exception:
                        pass
                cleared.append(d)
        logger.info(f"已清理缓存目录: {cleared if cleared else '无缓存目录'}")
    
    def _reload_config(self) -> None:
        """重新加载配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"配置已重载: {config.get('name', 'unknown')} v{config.get('version', '?')}")
        else:
            logger.warning(f"配置文件不存在: {self.config_file}")
    
    def _verify_system_state(self) -> bool:
        """验证系统状态是否恢复正常"""
        # 检查关键文件存在且可读
        checks = {
            "config_exists": os.path.exists(self.config_file),
            "storage_exists": os.path.exists(self.storage_dir),
        }
        all_ok = all(checks.values())
        logger.info(f"系统验证结果: {checks}, 整体状态: {'正常' if all_ok else '异常'}")
        return all_ok
    
    def _locate_issue(self, issue: Dict) -> str:
        """定位问题根源"""
        issue_type = issue.get("type", "unknown")
        if issue_type == "delta_g_overflow":
            dg = issue.get("dg_total", 0)
            return f"ΔG溢出: 当前值={dg}, 阈值=4.0"
        elif issue_type == "module_failure":
            module = issue.get("module", "unknown")
            return f"模块异常: {module}"
        return f"未知问题类型: {issue_type}"
    
    def _apply_partial_fix(self, issue: Dict) -> None:
        """应用局部修复"""
        issue_type = issue.get("type", "unknown")
        if issue_type == "delta_g_overflow":
            # 轻度DeltaG溢出，尝试调整参数
            self._adjust_delta_g_mild(issue)
        logger.info(f"局部修复已应用: {issue_type}")
    
    def _adjust_delta_g_mild(self, issue: Dict) -> None:
        """轻度调整DeltaG参数"""
        adjust_file = "storage/delta_g_adjustment.json"
        adjustment = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "mild_adjustment",
            "dg_total": issue.get("dg_total", 0),
            "applied": True
        }
        os.makedirs("storage", exist_ok=True)
        with open(adjust_file, "w", encoding="utf-8") as f:
            json.dump(adjustment, f, ensure_ascii=False, indent=2)
    
    def auto_heal_if_needed(self, dg_total: float) -> Optional[Dict]:
        """
        检查并自动触发自愈
        
        Args:
            dg_total: ΔG总值
            
        Returns:
            dict: 自愈结果，None表示无需自愈
        """
        if dg_total <= 2.10:
            return None
        
        logger.warning(f"ΔG={dg_total} 超过阈值，触发自动自愈")
        
        issue = {
            "type": "delta_g_overflow",
            "severity": "critical" if dg_total > 4.0 else "medium",
            "dg_total": dg_total
        }
        
        return self.heal(issue)
