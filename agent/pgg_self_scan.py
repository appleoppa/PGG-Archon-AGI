"""PGG Self-Scan Engine — 主动扫描知识缺口 → 写桥任务问用户。

核心机制：
1. 扫描 GeneDB → 发现低 coverage 的 domain/gate_type
2. 扫描 skill/workspace → 发现未入库的知识领域
3. 扫描外部参考（璇玑对齐表、论文）→ 发现缺失步
4. 汇总 → 写 bridge task（type=learn_suggest）→ 你决定学什么

运作模式：self-scan（不需要你先找材料，我找然后问你）
"""

import json
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
WATCHED_DOMAINS = [
    "agentic_rl",           # 强化学习agent
    "context_learning",     # 上下文学习
    "code_generation",      # 代码生成
    "tool_use",             # 工具调用
    "multi_agent",          # 多智能体
    "memory_architecture",  # 记忆架构
    "test_time_compute",    # 测试时计算
    "reward_modeling",      # 奖励建模
    "reasoning",            # 推理
    "safety_alignment",     # 安全对齐
    "evaluation",           # 评测
    "open_source_framework",# 开源框架
    "legal_reasoning",      # 法律推理
    "self_improvement",     # 自我改进
    "data_curation",        # 数据筛选
]

# 璇玑50步覆盖检查
XUANJI_STEPS = [
    (1, "基础ReAct架构"),
    (2, "思维链推理"),
    (3, "自我反思机制"),
    (4, "工具定义与执行"),
    (5, "长上下文处理"),
    (6, "记忆检索架构"),
    (7, "多步规划"),
    (8, "反馈学习"),
    (9, "环境交互"),
    (10, "错误恢复"),
    (11, "奖励建模"),
    (12, "探索-利用平衡"),
    (13, "策略梯度微调"),
    (14, "值函数估计"),
    (15, "世界模型建模"),
    (16, "因果推理"),
    (17, "反事实推理"),
    (18, "多假设推理"),
    (19, "主动信息收集"),
    (20, "不确定量化"),
    (21, "模型集成"),
    (22, "知识蒸馏"),
    (23, "持续学习"),
    (24, "灾难性遗忘规避"),
    (25, "元学习"),
    (26, "跨任务泛化"),
    (27, "指令遵循"),
    (28, "长度泛化"),
    (29, "分布外泛化"),
    (30, "对抗鲁棒性"),
    (31, "红队测试"),
    (32, "越狱检测"),
    (33, "价值观对齐"),
    (34, "安全护栏"),
    (35, "可解释性"),
    (36, "归因分析"),
    (37, "知识编辑"),
    (38, "微调数据构造"),
    (39, "RLHF/DMPO"),
    (40, "偏好对齐"),
    (41, "可扩展监督"),
    (42, "弱到强泛化"),
    (43, "计算最优训练"),
    (44, "自适应计算"),
    (45, "推测解码"),
    (46, "量化推理"),
    (47, "稀疏激活"),
    (48, "系统2慢思考"),
    (49, "自主Agent评测"),
    (50, "长期自主运行"),
]


def scan_gene_db_gaps() -> dict[str, Any]:
    """扫描 GeneDB 找 coverage 缺口。"""
    gaps = {}

    if not DB_PATH.exists():
        return {"error": f"GeneDB不存在: {DB_PATH}"}

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    # 总统计
    total = db.execute("SELECT COUNT(*) FROM evolution_genes").fetchone()[0]
    verified = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='verified'").fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='active'").fetchone()[0]
    candidate = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'").fetchone()[0]

    # 按 gate_type 分布
    gate_dist = defaultdict(int)
    gate_verified = defaultdict(int)
    for r in db.execute("SELECT status, gate_type FROM evolution_genes"):
        gt = r["gate_type"] or "unknown"
        gate_dist[gt] += 1
        if r["status"] == "verified":
            gate_verified[gt] += 1

    # 按 domain 分布（从 gene_name 中提取关键字匹配）
    domain_counts = defaultdict(int)
    for r in db.execute("SELECT gene_name, status FROM evolution_genes"):
        name = r["gene_name"] or ""
        for domain in WATCHED_DOMAINS:
            if domain.lower() in name.lower():
                domain_counts[domain] += 1

    # 璇玑50步覆盖
    xuanji_coverage = []
    # 搜索 gene_name, gate_type, absorbed_knowledge
    for step_num, step_name in XUANJI_STEPS:
        query = f"%{step_name}%"
        found = db.execute(
            "SELECT COUNT(*) FROM evolution_genes WHERE "
            "(gene_name LIKE ? OR gate_type LIKE ? OR absorbed_knowledge LIKE ?) "
            "AND status IN ('verified', 'active')",
            (query, query, query)
        ).fetchone()[0]
        if found == 0:
            xuanji_coverage.append({"step": step_num, "name": step_name, "covered": False})

    # 低覆盖率 domain（小于3条 verified）
    low_coverage_domains = [
        d for d in WATCHED_DOMAINS
        if domain_counts.get(d, 0) < 3
    ]

    db.close()

    return {
        "gene_db": {
            "total": total,
            "verified": verified,
            "active": active,
            "candidate": candidate,
        },
        "gate_distribution": dict(gate_dist),
        "domain_coverage": dict(domain_counts),
        "low_coverage_domains": low_coverage_domains,
        "xuanji_uncovered_steps": len(xuanji_coverage),
        "xuanji_uncovered_detail": xuanji_coverage[:10],  # 前10个未覆盖步
    }


def scan_skill_gaps() -> dict[str, Any]:
    """扫描已安装技能→找进化缺口。"""
    # 列出所有技能并匹配 domain
    try:
        from hermes_cli.skills import get_all_skill_entries
        skills = get_all_skill_entries()
        skill_names = [s.name for s in skills]
    except Exception:
        # fallback
        skill_dir = Path(os.path.expanduser("~/.hermes/skills"))
        if not skill_dir.exists():
            return {"skill_count": 0, "domain_gaps": []}
        skill_names = [d.name for d in skill_dir.iterdir() if d.is_dir()]

    # 匹配 domain
    domain_hits = defaultdict(list)
    for name in skill_names:
        for domain in WATCHED_DOMAINS:
            if domain.lower() in name.lower():
                domain_hits[domain].append(name)

    domains_without_skills = [
        d for d in WATCHED_DOMAINS if d not in domain_hits
    ]

    return {
        "skill_count": len(skill_names),
        "domains_with_skills": {d: hits for d, hits in domain_hits.items()},
        "domains_without_skills": domains_without_skills,
    }


def scan_recent_work() -> dict[str, Any]:
    """扫描最近的 workspace 活动 → 发现未归档的知识。"""
    workspace = Path(os.path.expanduser("~/.hermes/workspace"))
    recent_dirs = []
    if workspace.exists():
        for d in sorted(workspace.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            if d.is_dir():
                recent_dirs.append({
                    "name": d.name,
                    "modified": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
                })
    return {
        "recent_dirs": recent_dirs,
    }


def full_scan() -> dict[str, Any]:
    """完整扫描 → 汇总所有 gap。"""
    gene_gaps = scan_gene_db_gaps()
    skill_gaps = scan_skill_gaps()
    work = scan_recent_work()

    # 构建学习建议
    suggestions = []

    # 1. 璇玑未覆盖
    if gene_gaps.get("xuanji_uncovered_steps", 0) > 0:
        uncovered = gene_gaps.get("xuanji_uncovered_detail", [])
        steps_str = ", ".join([f"#{s['step']} {s['name']}" for s in uncovered[:5]])
        suggestions.append({
            "priority": "high",
            "category": "xuanji_gap",
            "uncovered_count": gene_gaps["xuanji_uncovered_steps"],
            "suggestion": f"璇玑有 {gene_gaps['xuanji_uncovered_steps']} 步未覆盖。前5: {steps_str}",
        })

    # 2. 低覆盖率 domain
    low = gene_gaps.get("low_coverage_domains", [])
    if low:
        suggestions.append({
            "priority": "medium",
            "category": "low_coverage_domain",
            "domains": low,
            "suggestion": f"以下 domain 低于3条verified基因: {', '.join(low[:6])}",
        })

    # 3. 无技能对应 domain
    no_skill = skill_gaps.get("domains_without_skills", [])
    if no_skill:
        suggestions.append({
            "priority": "low",
            "category": "no_skill_domain",
            "domains": no_skill,
            "suggestion": f"以下 domain 没有任何 skill: {', '.join(no_skill[:5])}",
        })

    # 4. candidate 堆积
    candidate_count = gene_gaps.get("gene_db", {}).get("candidate", 0)
    if candidate_count > 20:
        suggestions.append({
            "priority": "medium",
            "category": "candidate_backlog",
            "count": candidate_count,
            "suggestion": f"candidate 基因堆积 {candidate_count} 条，需批量审核",
        })

    scan_id = f"scan_{int(datetime.now().timestamp())}"

    return {
        "scan_id": scan_id,
        "created_at": datetime.now().isoformat(),
        "gene_db": gene_gaps,
        "skills": skill_gaps,
        "recent_activity": work,
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
        "boundary": "pgg_self_scan; local read-only scan; no LLM/network; no AGI/T5/ASI claim",
    }


# ─── 桥任务接入 ───


def scan_and_suggest() -> dict[str, Any]:
    """执行扫描 → 如果有建议 → 写 bridge task。"""
    scan = full_scan()
    
    if scan["suggestion_count"] == 0:
        return {"status": "no_gaps", "scan": scan}

    # 写桥任务
    from agent.pgg_execution_bridge import write_bridge_task

    tasks_written = []
    for s in scan["suggestions"][:3]:  # 最多3条避免泛滥
        task = write_bridge_task(
            "learn_suggest",
            payload={
                "priority": s["priority"],
                "category": s["category"],
                "suggestion": s["suggestion"],
                "details": {k: v for k, v in s.items() if k not in ("priority", "category", "suggestion")},
            },
            source="self_scan_engine",
        )
        if task.get("written"):
            tasks_written.append(task["task_id"])

    return {
        "status": "suggestions_written",
        "scan_id": scan["scan_id"],
        "suggestion_count": scan["suggestion_count"],
        "tasks_written": tasks_written,
        "scan": scan,
    }


# ─── CLI ───


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PGG Self-Scan Engine")
    parser.add_argument("--scan", action="store_true", help="执行知识缺口扫描")
    parser.add_argument("--suggest", action="store_true", help="扫描+写桥任务")
    parser.add_argument("--xuanji", action="store_true", help="仅检查璇玑50步覆盖")
    parser.add_argument("--domains", action="store_true", help="仅检查domain覆盖")
    args = parser.parse_args()

    if args.xuanji:
        gaps = scan_gene_db_gaps()
        print(json.dumps({
            "xuanji_uncovered": gaps.get("xuanji_uncovered_steps", 0),
            "detail": gaps.get("xuanji_uncovered_detail", []),
        }, indent=2, ensure_ascii=False))
        return

    if args.domains:
        gaps = scan_gene_db_gaps()
        print(json.dumps({
            "domain_coverage": gaps.get("domain_coverage", {}),
            "low_coverage": gaps.get("low_coverage_domains", []),
        }, indent=2, ensure_ascii=False))
        return

    if args.suggest:
        result = scan_and_suggest()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.scan:
        result = full_scan()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    parser.print_help()


if __name__ == "__main__":
    main()