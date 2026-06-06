---
name: pgg-archon-profile-bootstrap
description: PGG Archon / Apple Didi profile bootstrap — bounded writers for per-profile AGENTS.md, MEMORY.md, and skill sync. Idempotent, low-risk, rollback-friendly.
version: 0.1.0
author: Apple Didi (苹果弟弟)
license: MIT
metadata:
  hermes:
    tags: [pgg-archon, profile, bootstrap, agents-md, memory, skills]
    related_skills: [pgg-archon-truthful-agent-system-audit, pgg-archon-closed-loop-formula, super-evolution-21]
---

# PGG Archon Profile Bootstrap

> 主题：profile 级 AGENTS.md / MEMORY.md / skills 的"可重入、可回滚、可审计"引导层
> 状态：v0.1.0（已落地 2026-06-04）
> 边界：低/中风险 bootstrap 工具；不动 Hermes 核心 / Rust 扩展 / launchd 启动参数；不修改用户内容

## 0. 触发条件

Use when the user asks to:

- 给一个或多个 profile 写核心认知 Prompt（AGENTS.md）
- 给一个或多个 profile 初始化长期记忆 store（MEMORY.md）
- 把一个高分 profile 的 skills 同步给低分 profile（如 pgg-zhixing 31 → 90）
- 在不破坏 profile specialization 的前提下补齐 profile 引导层

Do NOT use this skill to:

- 修改 Hermes CLI / gateway / webui 任何代码
- 修改 launchd plist
- 删除任何文件（仅复制/创建）
- 改写 SOUL.md

## 1. 三个脚本

| 脚本 | 用途 | 行为 | 风险 |
|---|---|---|---|
| `agent/scripts/seed_profile_agents_md.py` | 写 AGENTS.md | `--profiles <p1 p2 ...> --template <path>`；idempotent；可 `--force` 重写 | low |
| `agent/scripts/init_profile_memory.py` | 写 MEMORY.md | 从 SOUL.md/skills/config.yaml 自动取 metadata 注入模板 | low |
| `agent/scripts/sync_profile_skills.py` | 复制 skills | `--target <p> --source <p> --exclude <substring>`；仅复制；不删 | medium |

## 2. 模板文件

- `agent/scripts/templates/agents_md_template.md` — 核心认知 Prompt 模板
- `agent/scripts/templates/memory_template.md` — 长期记忆模板

模板使用 Python str.format 占位符：`{profile}` `{topic}` `{generated_at}` `{soul_line}` `{skill_count}` `{provider_summary}`。

## 3. 标准执行顺序

```bash
cd ~/.hermes/hermes-agent
PY="$HOME/.hermes/hermes-agent/venv/bin/python"; [ -x "$PY" ] || PY=python3

# 1) 写 AGENTS.md（13 profile：default + 12 pgg-*）
$PY -m agent.scripts.seed_profile_agents_md \
  --profiles default pgg-zhixing pgg-xingshi pgg-minshi pgg-zhengju pgg-zhinao \
                pgg-anguan pgg-feisu pgg-guwen pgg-shenji pgg-tuiyan pgg-xunshi \
  --template agent/scripts/templates/agents_md_template.md

# 2) 写 MEMORY.md（同样 13 profile）
$PY -m agent.scripts.init_profile_memory \
  --profiles pgg-zhixing pgg-xingshi pgg-minshi pgg-zhengju pgg-zhinao \
             pgg-anguan pgg-feisu pgg-guwen pgg-shenji pgg-tuiyan pgg-xunshi \
             pgg-zhinao \
  --template agent/scripts/templates/memory_template.md

# 3) 同步 skills（仅在目标 profile 显著低于兄弟 profile 时执行）
$PY -m agent.scripts.sync_profile_skills \
  --target pgg-zhixing --source pgg-xingshi
```

## 4. 验证清单

```bash
echo "AGENTS.md count: $(ls -1 $HOME/.hermes/profiles/*/AGENTS.md | wc -l) (期望 13)"
echo "MEMORY.md count: $(ls -1 $HOME/.hermes/profiles/*/MEMORY.md | wc -l) (期望 13)"
for p in $HOME/.hermes/profiles/pgg-*/skills; do
  echo "$(basename $(dirname $p)): $(ls -1 $p | wc -l)"
done
```

## 5. 回滚

```bash
# 删除本轮写入的 AGENTS.md / MEMORY.md（脚本都是创建型，不删 skills）
find ~/.hermes/profiles -name AGENTS.md -newer <marker> -delete
find ~/.hermes/profiles -name MEMORY.md -newer <marker> -delete
# skills 同步的回滚：从 ~/.hermes/workspace/config-backups/zhixing_skills_<ts>/ 复制回去
```

## 6. Pitfalls (2026-06-04)

- **重复 run 命中 idempotency 路径会跳过**：脚本故意 idempotent；显式要重写必须 `--force`。
- **pgg-zhixing skills 同步时 default 5 个不能作 source**：default skills 是 5 个内置 skills 集；同步自 default 会无效；同步自 pgg-xingshi（88 个）才有意义。
- **profile specialization 保护**：sync_profile_skills 默认 `--exclude` 为空；如果目标 profile 已有的 skills 表示其特化（如法律专用 skills），不要用 `--force` 全替换；用 `--exclude` 排除目标特有。
- **template 渲染失败会被脚本静默**：模板里写了不存在占位符时 `str.format` 会抛 KeyError；先在一次小范围 dry-run 上验证模板再批量跑。

## 7. 关联入口

- 真实脚本：`~/.hermes/hermes-agent/agent/scripts/`
- 真实模板：`~/.hermes/hermes-agent/agent/scripts/templates/`
- 真实 commit（2026-06-04）：`8dfb83cc2 P1: profile bootstrap scripts and templates (AGENTS, MEMORY, skills sync)`
- 治理目录：`~/.hermes/workspace/治理/`
- 总账：`~/.hermes/data/EVOLUTION_MANIFEST.json`（key: `latest_p1_apply_20260604`）
