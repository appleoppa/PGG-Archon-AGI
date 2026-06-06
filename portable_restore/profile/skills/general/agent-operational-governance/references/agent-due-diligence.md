# Agent Due Diligence — Absorbed Detail

Original skill: `agent-due-diligence`.

## Core Lessons

- 汇报前必须核实工作区状态、数据质量与任务范围。
- 全量扫描，不依赖配置声明；配置路径不存在不等于资源不存在。
- 内容溯源必须读 frontmatter、正文标记、创建/迁移线索；不要从目录位置推断来源。
- 验证代码级依赖，不能靠文件名推断脚本读取关系。
- 检查数据质量，不只检查文件存在。
- 不要从简单指令推导复杂系统。
- 迁移完成不等于验证通过。
- 声明修复不等于实质修复：读回 patch、DB、目录迁移结果。
- 审计顺序必须是数据修改后再做质量检查。
- 审计阶段自己的问题发现也必须工具核验。
- Hermes profile 环境下 `~` 可能指向 profile home，关键路径用绝对路径。

## Repeated Failure Modes

| 场景 | 后果 | 防线 |
|---|---|---|
| 只查配置路径不扫描 workspace | 误判资源缺失或已修复 | 全工作区搜索 + 绝对路径重试 |
| 文件名像配置就推断被读取 | 扩散错误依赖关系 | search_files 验证引用链 |
| 只看 status/exit_code | 假完成 | 检查业务产物 |
| 修改后未 SELECT/读回 | 声明修复但内容未变 | 写后读回 |
| 提交前跑质量审计 | 漏检本轮数据 | INSERT/UPDATE → SELECT → 审计 |

## Health Audit Dimensions

1. 脚本存在性：SKILL.md 引用 scripts/ 时确认文件存在。
2. 描述时效性：抽查 description 是否仍准确。
3. 引用一致性：related_skills 是否可解析。
4. 零字节/空文件：扫描空 SKILL.md 或空目录。
5. 使用频率仅作线索，不作价值判断。

## References Preserved

Original skill had detailed references for vector library migration, Feishu overreach, system health assessment, gene DB audit, retroactive traceability, and evolution-gene SQL. Those remain in the archived original directory if full incident detail is needed.
