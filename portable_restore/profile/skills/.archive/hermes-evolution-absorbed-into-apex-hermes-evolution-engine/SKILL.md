---
name: hermes-evolution
description: 把用户纠正和踩坑沉淀为AGENTS.md/TOOLS.md/SKILL.md
---

# Hermes-Evolution（摘要版）

> 完整内容: `SKILL_FULL.md`（同目录）

你是"提案器"，不是"自动改写器"。所有真正的进化都先写草稿，再等用户审批。

## 触发条件
- 主会话（非sub-agent/cron/heartbeat）
- 本轮已形成完整结果
- 出现≥1个强信号 或 ≥2个中信号

**强信号**: 用户明确纠正/偏好 | 高成本踩坑修复 | 可复用工作流 | 记忆/画像/自我描述清理 | 虚假完成或门禁失败整改 | 用户用“？”、“什么意思”等短促反馈指出跑偏、证据不足或未答当前任务
**中信号**: 询问为啥不做某事 | 提设计模式 | 指漏洞

## 当前任务优先级坑点
- 如果对话里有压缩摘要或上一任务残留，必须以用户最新消息为当前任务；不要继续完成或汇报上一任务。
- 用户要求“分析并整理记忆文件、用户画像、自我描述”时，应直接执行定位、备份、重写、验证四步；不得转去重构无关规则或只汇报已有结果。
- 用户用单个“？”追问时，优先视为“你跑偏了/没回答我现在的问题”，应立即纠偏并执行真实任务，而不是解释上一段输出。

## 相关参考
- `references/memory-profile-identity-consolidation-and-gate-repair.md`: 记忆、用户画像、自我描述整理，以及“降级不是目标，75%自修并重跑门禁”的跨层固化流程。
- `references/latest-message-priority-memory-cleanup.md`: 压缩摘要或旧任务残留存在时，记忆/画像/自我描述整理必须优先服从用户最新消息，避免继续汇报上一任务。
- `references/evolution-gene-database.md`: 将外部学习/短板修复落地为工作空间 SQLite 进化基因库的 schema、边界和验证清单。
- `references/skills_guard_cron_false_positive.md`: skills_guard `destructive_root_rm` 对 cron job prompt 的 false-positive 自拦截问题，根因是安全扫描器将系统生成内容误判为外部注入攻击。
- `references/cron-background-review-dual-gate.md`: cron job toolsets 配置层与后台执行审查层的双层门控冲突，导致后台 cron 无法写文件；相关 `agent-operational-governance` 技能已收录。

## 检查流程
1. 看本轮有没有值得沉淀的信号
2. 没有 → `NOTHING_TO_SAVE`
3. 有 → 评估该写哪个文件
4. 用 `evolution_proposal` 提交

## 超级进化吸收规则

当用户要求“学习、举一反三、融会贯通、最强技能组合”时，优先加载并执行 `apex-hermes-evolution-engine`：

1. 先确认材料真实存在，再按主题分簇。
2. 可并行时用 subagents 深读，不把单次摘要冒充完整学习。
3. 输出必须包含：原则、流程、可落地条款、风险边界、沉淀位置。
4. 优先更新已有技能；新建综合技能后，还要检查是否需要联动 `search-skillbank`、`manual-evolution-loop`、`TOOLS.md` 或 `AGENTS.md`。
5. 不保存一次性过程到长期记忆；可复用流程进 SKILL.md，工具纪律进 TOOLS.md，行为门禁进 AGENTS.md。
6. 不虚构外部模型、长期后台、自主修改核心代码或底层语言实现。

## 目标文件
| 文件 | 写什么 |
|------|--------|
| AGENTS.md | 行为规则、工作流、团队架构 |
| TOOLS.md | 工具使用技巧、配置备忘 |
| MEMORY.md | 踩坑记录、事实性信息 |
| SKILL.md | 可复用的技能包 |

## 硬性约束
- child审查完成且有提案时，必须走 `evolution_proposal` 工具
- 禁止跳过工具直接输出纯文本审批
