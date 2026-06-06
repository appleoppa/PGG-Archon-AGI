# OpenClaw → Hermes 系统迁移映射参考

> 苹果中枢整体迁移 (2026-05-16)
> 源: `~/.openclaw-autoclaw/` (8,898 files, 453MB)
> 目标: `~/.hermes/` (7,050 files migrated, 78.2%)

## 路径映射

| 区域 | OpenClaw路径 | Hermes路径 |
|------|-------------|-----------|
| 主工作空间 | `~/.openclaw-autoclaw/workspace` | `~/.hermes/workspace` |
| 主规则 (AGENTS.md) | `workspace/AGENTS.md` | `workspace/AGENTS.md` |
| 记忆索引 | `workspace/MEMORY.md` | `workspace/MEMORY.md` |
| 身份定义 | `workspace/SOUL.md` | `workspace/SOUL.md` |
| 工具指南 | `workspace/TOOLS.md` | `workspace/TOOLS.md` |
| 用户画像 | `workspace/USER.md` | `workspace/USER.md` |
| 心跳/身份 | `workspace/HEARTBEAT.md`, `IDENTITY.md` | `workspace/HEARTBEAT.md`, `IDENTITY.md` |
| 会话状态 | `workspace/session_state.json` | `workspace/session_state.json` |
| 主配置 | `openclaw.json` | `~/.hermes/openclaw.json` (参考用) |
| Hermes配置 | (不存在, Hermes原生) | `~/.hermes/config.yaml` |
| 统一配置 | `workspace/config/superagent.yaml` | `workspace/config/superagent.yaml` |
| 路由配置 | `workspace/config/router_config.yaml` | `workspace/config/router_config.yaml` |
| 技能路由 | `workspace/config/skill_routing.yaml` | `workspace/config/skill_routing.yaml` |
| MCP配置 | `workspace/config/mcp/*.json` | `workspace/config/mcp/*.json` |
| 办案库(活跃) | `workspace/苹果中枢办案库/` | `workspace/办案库/` (重命名) |
| 办案库(存档) | `workspace/苹果中枢办案库/_存档/` | `workspace/办案库/_存档/` |
| 法律法规库 | `workspace/智库/法律法规库/` | `workspace/智库/法律法规库/` |
| 开智进化数据 | `workspace/开智/` | `workspace/开智/` |
| 审计队列 | `workspace/审计队列/` | `workspace/审计队列/` |
| 任务队列 | `workspace/任务队列/` | `workspace/任务队列/` |
| 工作流模板 | `workspace/workflows/` | `workspace/workflows/` |
| 标准细则 | `workspace/standards/` | `workspace/standards/` |
| 脚本工具 | `workspace/scripts/` | `workspace/scripts/` |
| 辅助工具 | `workspace/tools/` | `workspace/tools/` |
| 每日记忆 | `workspace/memory/` | `workspace/memory/` |
| 团队规则 | `workspace/team-rules/` | `migration/team-rules/` |
| 进化草案 | `workspace/evolution-drafts/` | `migration/evolution-drafts/` |
| 运行日志 | `workspace/logs/` | `workspace/logs/` |
| 部门身份文件 | `agents/*/workspace/` | `~/.hermes/agents/*/workspace/` |
| 原始技能(51个) | `skills/` | `~/.hermes/skills/` |
| 复刻部门技能(15个) | (Hermes原生) | `~/.hermes/skills/` |
| 部门深层分科 | `agents/*/workspace/skills/*/` | `~/.hermes/agents/*/workspace/skills/*/` |
| 部门会话 | `agents/*/sessions/` | `~/.hermes/agents/*/workspace/sessions/` |
| 向量数据库 | `workspace/向量库/` | `migration/向量库/` (参考用) |
| Git历史 | `workspace/.git/` | `migration/workspace-git/` (参考用) |
| 会话历史(17个) | `autoclaw/` | `migration/autoclaw-chat-history/` |
| Cron执行记录 | `cron/` | `migration/cron/` |
| 交付队列 | `delivery-queue/` | `migration/delivery-queue/` |
| 自改进反思 | `~/self-improving/` | `~/.hermes/workspace/self-improving/` |

## 架构映射

| OpenClaw概念 | Hermes等价物 | 说明 |
|-------------|-------------|------|
| `sessions_spawn agentId="xxx"` | `delegate_task(skills=[...])` | 子智能体调度 |
| `openclaw cron run <id>` | `cronjob(action='run', job_id=...)` | Cron任务管理 |
| `openclaw gateway restart` | 编辑 `~/.hermes/config.yaml` | 配置热加载 |
| `agents.list[id=main].subagents.allowAgents` | Hermes系统内部管理 | 授权不再需要手动配置 |
| `openclaw.json` | `config.yaml` + `superagent.yaml` | 配置分两层 |
| Config Guard (cp + restart) | 直接编辑config.yaml | 不需要额外步骤 |
| `subagents list` | `process(action='list')` | 进程管理 |

## 迁移中跳过的内容

| 项目 | 大小 | 理由 |
|------|------|------|
| browser/Chrome缓存 | 163MB, 3,517文件 | Hermes有自己的浏览器系统 |
| API密钥 (openclaw.json中) | -- | 用户明确拒绝迁移 |
| Feishu通道配置 | -- | 用户明确拒绝迁移 |

## 迁移后落位检查流程

当完成迁移后，按以下步骤验证所有路径和命令已正确更新:

1. **全域扫描旧路径残留**:
   ```bash
   grep -rl 'openclaw-autoclaw' ~/.hermes --include='*.md' --include='*.yaml' \
       --include='*.py' --include='*.sh' --include='*.json' 2>/dev/null
   ```

2. **分类过滤**:
   - 跳过: `node_modules`, `.git/`, `migration/`, `sessions/`, `memory/`, `开智/`, `智库/`, `办案库/`, `logs/`
   - 需要更新: 所有在核心区域找到的文件

3. **批量更新** (standards/scripts/tools):
   ```bash
   find . -name '*.md' -exec sed -i '' 's|old|new|g' {} \;
   ```

4. **靶向修补** (关键配置文件):
   使用 `patch` 工具逐个修复TOOLS.md, AGENTS.md, superagent.yaml

5. **终验**:
   ```bash
   grep -rl 'openclaw-autoclaw' . [filters] | wc -l
   # 预期: 0
   ```

## 核心坑点

- **路径替换顺序**: 先替换 `.openclaw-autoclaw` → `.hermes`, 不要只替换目录名部分
- **避免触及API密钥**: openclaw.json中的API密钥行不要批量替换, 只替换workspace路径
- **映射表文件**: 作为文档的对照表(显示Old→New)中的旧路径是故意的, 不要更新
- **历史数据 vs 运行数据**: session文件/基因档案/记忆日志中的旧路径不需要改
