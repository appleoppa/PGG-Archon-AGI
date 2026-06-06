#!/usr/bin/env python3
"""
技能候选萃取脚本 — 从近期会话中提取可能值得沉淀为技能的模式。

用法：
    python3 extract_candidates.py [--days 7]

输出：JSON 格式的候选模式列表，每条包含：
  - pattern_type: "correction" | "workflow" | "technique" | "pitfall" | "tool_usage"
  - trigger_phrase: 用户触发此模式时的常用表述
  - description: 模式做什么
  - key_steps: 关键步骤（简述）
  - evidence: 来自哪个会话、什么场景
  - frequency: 此模式出现的次数
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# ── 配置 ─────────────────────────────────────────────────────────────
HERMES_HOME = os.path.expanduser("~/.hermes")
SESSIONS_DIR = os.path.join(HERMES_HOME, "agents", "main", "sessions")
OUTPUT_DIR = os.path.join(HERMES_HOME, "workspace", "技能萃取")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 默认搜索最近 7 天
DEFAULT_DAYS = 7
MAX_SESSIONS = 20  # 最多分析的会话数


# ── 会话扫描 ─────────────────────────────────────────────────────────

def get_recent_session_files(days: int):
    """获取最近 N 天的会话文件（按修改时间过滤）。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    files = []
    if not os.path.isdir(SESSIONS_DIR):
        print(f"[WARN] 会话目录不存在: {SESSIONS_DIR}", file=sys.stderr)
        return files

    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".jsonl"):
            continue
        if ".deleted." in fname or ".reset." in fname:
            continue
        fpath = os.path.join(SESSIONS_DIR, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
        if mtime >= cutoff:
            files.append(fpath)

    # 按修改时间排序，最新的在前
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[:MAX_SESSIONS]


def scan_session_for_patterns(filepath: str):
    """
    扫描单个会话文件，识别潜在模式信号。

    信号类型：
    - correction: 用户纠正 agent 行为的消息
    - workflow: 涉及 3+ 步骤的复杂任务
    - technique: 技术性操作或配置
    - pitfall: 重复出现的错误
    - tool_usage: 工具使用模式
    """
    signals = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        return signals

    session_id = os.path.splitext(os.path.basename(filepath))[0]
    conversation = []
    user_msgs = []
    assistant_msgs = []
    tool_calls_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") != "message":
            continue

        msg = entry.get("message", {})
        role = msg.get("role")
        content = msg.get("content", [])
        text_parts = [
            c.get("text", "") for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
        text = " ".join(text_parts)

        if role == "user":
            user_msgs.append(text)
        elif role == "assistant":
            assistant_msgs.append(text)
            # 统计工具调用
            for c in content:
                if isinstance(c, dict) and c.get("type") == "toolCall":
                    tool_calls_count += 1

    if not user_msgs and not assistant_msgs:
        return signals

    # ── 信号 1: 用户纠正 ──
    correction_patterns = [
        r"不要", r"不是", r"错了", r"不对", r"错误", r"别",
        r"记住", r"注意", r"纠正", r"误会",
        r"don't", r"not\s+that", r"wrong", r"incorrect",
        r"remember", r"instead",
    ]
    for msg in user_msgs:
        for pat in correction_patterns:
            if re.search(pat, msg, re.IGNORECASE):
                # 提取纠正的上下文
                signals.append({
                    "session_id": session_id,
                    "pattern_type": "correction",
                    "user_message": msg[:500],
                    "context": f"用户纠正出现在会话 {session_id}",
                })
                break

    # ── 信号 2: 复杂工作流（多步任务） ──
    if tool_calls_count >= 5:
        signals.append({
            "session_id": session_id,
            "pattern_type": "workflow",
            "tool_calls_count": tool_calls_count,
            "user_goal": user_msgs[0][:300] if user_msgs else "未知",
            "context": f"涉及 {tool_calls_count} 个工具调用的复杂任务",
        })

    # ── 信号 3: 技术操作 ──
    tech_patterns = [
        r"install", r"configure", r"setup", r"部署", r"安装", r"配置",
        r"docker", r"git\s+clone", r"pip\s+install", r"npm\s+install",
        r"ssh", r"api.?key", r"token", r"provider", r"model",
        r"migrate", r"迁移", r"备份",
    ]
    for msg in user_msgs + assistant_msgs:
        for pat in tech_patterns:
            if re.search(pat, msg, re.IGNORECASE):
                signals.append({
                    "session_id": session_id,
                    "pattern_type": "technique",
                    "evidence": msg[:300],
                    "context": f"技术操作在会话 {session_id}",
                })
                break

    # ── 信号 4: 错误/异常 ──
    error_patterns = [
        r"error", r"traceback", r"exception", r"fail", r"failed",
        r"timeout", r"拒绝", r"异常", r"失败",
    ]
    for msg in assistant_msgs:
        for pat in error_patterns:
            if re.search(pat, msg, re.IGNORECASE):
                signals.append({
                    "session_id": session_id,
                    "pattern_type": "pitfall",
                    "error_context": msg[:300],
                })
                break

    # ── 信号 5: 重复操作 ──
    tool_names = set()
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message", {})
        content = msg.get("content", [])
        for c in content:
            if isinstance(c, dict) and c.get("type") == "toolCall":
                tool_names.add(c.get("name", ""))

    common_tools = {"terminal", "read_file", "write_file", "search_files", "web_search"}
    overlap = tool_names & common_tools
    if len(overlap) >= 3:
        signals.append({
            "session_id": session_id,
            "pattern_type": "tool_usage",
            "tools_used": list(tool_names),
            "context": f"工具组合使用模式",
        })

    return signals


def deduplicate_signals(signals):
    """合并同类信号，基于 description 和 pattern_type 去重。"""
    seen = {}
    for sig in signals:
        key = (sig.get("pattern_type"), sig.get("user_message", "")[:100])
        if key not in seen:
            seen[key] = sig
            seen[key]["frequency"] = 1
        else:
            seen[key]["frequency"] += 1
    return list(seen.values())


def load_existing_skills():
    """加载现有技能列表用于去重比对。"""
    skills_dir = os.path.join(HERMES_HOME, "skills")
    skills = []
    if not os.path.isdir(skills_dir):
        return skills
    for item in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, item, "SKILL.md")
        if os.path.isfile(skill_path):
            skills.append({"name": item, "path": skill_path})
    return skills


def check_duplicate(candidate_name: str, candidate_desc: str, existing_skills: list) -> dict:
    """
    简单比对候选与现有技能的重复度。

    返回：
        {
            "is_duplicate": True/False,
            "matches": ["skill-name", ...],
            "similarity": 0.0-1.0,
            "recommendation": "create_new" | "merge_into" | "skip"
        }
    """
    best_match = None
    best_sim = 0.0

    cname_words = set(candidate_name.lower().replace("-", " ").split())
    cdesc_words = set(re.findall(r"[a-zA-Z\u4e00-\u9fff]{2,}", candidate_desc.lower()))

    for skill in existing_skills:
        sname = skill["name"]
        sname_words = set(sname.lower().replace("-", " ").split())

        # 名称重叠
        name_overlap = len(cname_words & sname_words) / max(len(cname_words | sname_words), 1)

        # 读取 SKILL.md 做描述比对
        try:
            with open(skill["path"], "r", encoding="utf-8") as f:
                scontent = f.read(2000)
            sdesc_match = re.search(r"description:\s*\"(.+?)\"", scontent)
            sdesc = sdesc_match.group(1) if sdesc_match else ""
            sdesc_words = set(re.findall(r"[a-zA-Z\u4e00-\u9fff]{2,}", sdesc.lower()))
            desc_overlap = len(cdesc_words & sdesc_words) / max(len(cdesc_words | sdesc_words), 1) if (cdesc_words or sdesc_words) else 0
        except (OSError, UnicodeDecodeError):
            desc_overlap = 0

        similarity = max(name_overlap * 0.5, desc_overlap * 0.5)
        if similarity > best_sim:
            best_sim = similarity
            best_match = sname

    if best_sim >= 0.50:
        return {
            "is_duplicate": True,
            "matches": [best_match],
            "similarity": round(best_sim, 2),
            "recommendation": "skip",
        }
    elif best_sim >= 0.25:
        return {
            "is_duplicate": False,
            "matches": [best_match],
            "similarity": round(best_sim, 2),
            "recommendation": "merge_into",
        }
    else:
        return {
            "is_duplicate": False,
            "matches": [],
            "similarity": round(best_sim, 2),
            "recommendation": "create_new",
        }


def generate_candidate_name(description: str, pattern_type: str) -> str:
    """从描述中生成候选技能名称雏形。"""
    # 提取关键词
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]{3,}", description.lower())
    # 去停用词
    stopwords = {"the", "and", "for", "with", "from", "that", "this", "to", "of", "in", "on", "at", "by", "is", "are"}
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    if not filtered:
        return f"auto-{pattern_type}-{datetime.now().strftime('%m%d')}"
    return "-".join(filtered[:4])


def main():
    days = DEFAULT_DAYS
    if len(sys.argv) > 1 and sys.argv[1] == "--days":
        try:
            days = int(sys.argv[2])
        except (IndexError, ValueError):
            pass

    print(f"[Scan] 扫描过去 {days} 天的会话日志...")
    session_files = get_recent_session_files(days)
    print(f"[Scan] 找到 {len(session_files)} 个近期会话文件")

    # 阶段一：扫描
    all_signals = []
    for fpath in session_files:
        try:
            signals = scan_session_for_patterns(fpath)
            all_signals.extend(signals)
        except Exception as e:
            print(f"[WARN] 扫描 {fpath} 时出错: {e}", file=sys.stderr)

    print(f"[Scan] 原始信号: {len(all_signals)} 条")

    # 去重
    deduped = deduplicate_signals(all_signals)
    print(f"[Dedup] 去重后: {len(deduped)} 条")

    # 阶段二：比对去重
    existing_skills = load_existing_skills()
    print(f"[Compare] 现有技能: {len(existing_skills)} 个")

    candidates = []
    for sig in deduped:
        desc = sig.get("user_message", "") or sig.get("error_context", "") or sig.get("evidence", "") or sig.get("context", "")
        name = generate_candidate_name(desc, sig.get("pattern_type", "unknown"))
        dup_check = check_duplicate(name, desc, existing_skills)

        candidates.append({
            "candidate_name": name,
            "pattern_type": sig.get("pattern_type", "unknown"),
            "description": desc[:500],
            "frequency": sig.get("frequency", 1),
            "duplicate_check": dup_check,
            "source_session": sig.get("session_id", ""),
            "timestamp": datetime.now().isoformat(),
        })

    # 分类输出
    to_create = [c for c in candidates if c["duplicate_check"]["recommendation"] == "create_new"]
    to_merge = [c for c in candidates if c["duplicate_check"]["recommendation"] == "merge_into"]
    to_skip = [c for c in candidates if c["duplicate_check"]["recommendation"] == "skip"]

    # 阶段三：质量审查 + 阶段四：提案
    report = {
        "generated_at": datetime.now().isoformat(),
        "scan_days": days,
        "sessions_scanned": len(session_files),
        "total_signals": len(all_signals),
        "after_dedup": len(deduped),
        "summary": {
            "to_create": len(to_create),
            "to_merge": len(to_merge),
            "to_skip": len(to_skip),
        },
        "candidates": {
            "recommended_create": to_create,
            "recommended_merge": to_merge,
            "skipped": to_skip,
        },
    }

    # 写入报告文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"proposal_{timestamp}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"技能萃取提案已完成")
    print(f"{'='*50}")
    print(f"  扫描会话:     {len(session_files)}")
    print(f"  原始信号:     {len(all_signals)}")
    print(f"  去重后:       {len(deduped)}")
    print(f"  建议创建:     {len(to_create)}")
    print(f"  建议合并:     {len(to_merge)}")
    print(f"  已跳过:       {len(to_skip)}")
    print(f"{'='*50}")
    print(f"  报告已保存: {output_path}")
    print()

    # 简要输出每条候选
    if to_create:
        print("--- 建议创建 ---")
        for c in to_create:
            print(f"  [{c['pattern_type']}] {c['candidate_name']}")
            print(f"    描述: {c['description'][:100]}...")
            print(f"    频次: {c['frequency']}")
            print()

    if to_merge:
        print("--- 建议合并 ---")
        for c in to_merge:
            print(f"  [{c['pattern_type']}] {c['candidate_name']}")
            print(f"    合并入: {c['duplicate_check']['matches'][0]}")
            print()

    # 输出 JSON 到 stdout 方便 cron 捕获
    print("---JSON_START---")
    print(json.dumps(report, ensure_ascii=False))
    print("---JSON_END---")


if __name__ == "__main__":
    main()
