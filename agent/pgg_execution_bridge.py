"""PGG Execution Bridge — 自循环→可执行动作的桥梁。
Phase 1: 自循环产任务文件 → 桥审查 → 执行/通知

设计：
- 自循环在Phase2/Phase3等注入桥调用
- 桥写JSON任务文件到 ~/.hermes/workspace/execution-bridge/tasks/
- 可在本session或独立脚本中处理任务
- 所有执行记录写入 ledger

边界：
- 不修改Hermes core/provider/scheduler/security
- 不自动执行LLM调用（任务标注need_llm_check=True）
- 不自动创建PR（任务标注need_human_review=True）
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

BRIDGE_DIR = Path(os.path.expanduser("~/.hermes/workspace/execution-bridge"))
TASKS_DIR = BRIDGE_DIR / "tasks"
LEDGER_DIR = BRIDGE_DIR / "ledger"
DONE_DIR = BRIDGE_DIR / "done"

SCHEMA = "pgg_execution_bridge/v1"


def _now() -> str:
    return datetime.now().isoformat()


def _ensure_dirs():
    for d in [BRIDGE_DIR, TASKS_DIR, LEDGER_DIR, DONE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ─── 任务类型定义 ───

TASK_TEMPLATES = {
    "promotion": {
        "description": "candidate基因需要LLM审核才能promote",
        "need_llm_check": True,
        "can_auto_execute": False,
        "fields": ["gene_ids", "count", "reason"],
    },
    "skill_gen": {
        "description": "高fitness融合子代需要生成skill草案",
        "need_llm_check": True,
        "can_auto_execute": False,
        "fields": ["gene_ids", "fitnesses", "reason"],
    },
    "config_fix": {
        "description": "修复配置文件（自动备份+验证+回滚保护）",
        "need_llm_check": False,
        "can_auto_execute": True,
        "fields": ["file", "old_string", "new_string", "reason", "rollback_plan"],
    },
    "code_fix": {
        "description": "修复代码（自动备份+语法验证+回滚保护）",
        "need_llm_check": False,
        "can_auto_execute": True,
        "fields": ["file", "old_string", "new_string", "reason", "rollback_plan"],
    },
    "learn_suggest": {
        "description": "自扫描发现知识缺口，建议用户学习特定主题",
        "need_llm_check": False,
        "can_auto_execute": False,
        "fields": ["priority", "category", "suggestion", "details"],
    },
    "alert": {
        "description": "健康检测异常通知",
        "need_llm_check": False,
        "can_auto_execute": True,
        "fields": ["alert_type", "severity", "detail"],
    },
    "saturation_switch": {
        "description": "PicoAPEX饱和检测建议切换维度",
        "need_llm_check": True,
        "can_auto_execute": False,
        "fields": ["current_dim", "elite_ratio", "saturated", "suggested_dim"],
    },
}


# ─── 写任务文件 ───


def write_bridge_task(
    task_type: str,
    payload: dict[str, Any],
    source: str = "self_evolution_loop",
) -> dict[str, Any]:
    """写一个执行桥任务文件。
    
    Args:
        task_type: promotion/skill_gen/alert/saturation_switch
        payload: 任务数据
        source: 来源模块名
        
    Returns: 任务元数据
    """
    _ensure_dirs()
    
    if task_type not in TASK_TEMPLATES:
        return {"error": f"Unknown task type: {task_type}", "written": False}
    
    template = TASK_TEMPLATES[task_type]
    task_id = f"{task_type}_{int(time.time())}_{os.urandom(4).hex()}"
    
    task = {
        "schema": SCHEMA,
        "task_id": task_id,
        "task_type": task_type,
        "created_at": _now(),
        "source": source,
        "need_llm_check": template["need_llm_check"],
        "can_auto_execute": template["can_auto_execute"],
        "status": "pending",
        "payload": payload,
    }
    
    filepath = TASKS_DIR / f"{task_id}.json"
    with open(filepath, "w") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)
    
    return {
        "written": True,
        "task_id": task_id,
        "filepath": str(filepath),
        "need_llm_check": template["need_llm_check"],
    }


# ─── 读任务队列 ───


def list_pending_tasks() -> list[dict[str, Any]]:
    """列出所有待处理任务。"""
    _ensure_dirs()
    tasks = []
    for fpath in sorted(TASKS_DIR.glob("*.json")):
        try:
            with open(fpath) as f:
                task = json.load(f)
            if task.get("status") == "pending":
                tasks.append(task)
        except (json.JSONDecodeError, OSError):
            continue
    return tasks


def read_task(task_id: str) -> Any:
    """按ID读取单个任务。"""
    _ensure_dirs()
    for fpath in TASKS_DIR.glob(f"{task_id}.json"):
        try:
            with open(fpath) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


# ─── 标记任务 ───


def mark_task(task_id: str, status: str, note: str = "") -> dict[str, Any]:
    """标记任务状态：approved/rejected/processing/done/error。
    
    标记为 done/error 时自动移到 done/ 目录。
    """
    _ensure_dirs()
    for fpath in TASKS_DIR.glob(f"{task_id}.json"):
        try:
            with open(fpath) as f:
                task = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"error": "cannot_read_task"}
        
        task["status"] = status
        task["processed_at"] = _now()
        if note:
            task["note"] = note
        
        # 终态 → 归档
        if status in ("done", "error", "rejected"):
            # 写 ledger
            ledger_path = LEDGER_DIR / f"{task_id}.ledger.json"
            with open(ledger_path, "w") as f:
                json.dump(task, f, indent=2, ensure_ascii=False)
            
            # 移动到 done/
            dest = DONE_DIR / fpath.name
            fpath.rename(dest)
            return {
                "moved": True,
                "final_status": status,
                "ledger_path": str(ledger_path),
                "archived_path": str(dest),
            }
        else:
            # 更新原文件
            with open(fpath, "w") as f:
                json.dump(task, f, indent=2, ensure_ascii=False)
            return {"updated": True, "status": status}
    
    return {"error": f"task_{task_id}_not_found"}


# ─── 统计数据 ───


def bridge_stats() -> dict[str, Any]:
    """Execution Bridge 统计数据。"""
    _ensure_dirs()
    
    pending = list_pending_tasks()
    done_files = list(DONE_DIR.glob("*.json"))
    ledger_files = list(LEDGER_DIR.glob("*.ledger.json"))
    
    by_type: dict[str, int] = {}
    for t in pending:
        tt = t.get("task_type", "unknown")
        by_type[tt] = by_type.get(tt, 0) + 1
    
    by_status: dict[str, int] = {}
    for f in done_files:
        try:
            with open(f) as fh:
                data = json.load(fh)
            st = data.get("status", "unknown")
            by_status[st] = by_status.get(st, 0) + 1
        except (json.JSONDecodeError, OSError):
            pass
    
    return {
        "schema": f"{SCHEMA}/stats",
        "created_at": _now(),
        "pending_count": len(pending),
        "done_count": len(done_files),
        "ledger_count": len(ledger_files),
        "by_type": by_type,
        "by_final_status": by_status,
    }


# ─── 命令行 ───


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PGG Execution Bridge")
    parser.add_argument("--stats", action="store_true", help="显示统计数据")
    parser.add_argument("--list", action="store_true", help="列出待处理任务")
    parser.add_argument("--process", type=str, help="处理指定任务ID")
    parser.add_argument("--status", type=str, choices=["approved", "rejected", "done", "error"],
                        default="done", help="标记状态 (默认 done)")
    parser.add_argument("--note", type=str, default="", help="处理备注")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = bridge_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return
    
    if args.list:
        tasks = list_pending_tasks()
        if not tasks:
            print("没有待处理任务")
            return
        for t in tasks:
            print(f"  [{t['task_type']:20s}] {t['task_id'][:30]:30s} | LLM={'Y' if t.get('need_llm_check') else 'N'} | auto={'Y' if t.get('can_auto_execute') else 'N'}")
        return
    
    if args.process:
        result = mark_task(args.process, args.status, note=args.note)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()