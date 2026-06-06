# V7.2 Kanban 原生办案链路

## 触发场景

当用户说“开始办案 / 执行办案 / 启动办案 / 开案”，且属于正式案件或长文书办理时，不能只生成部门 Markdown；必须进入 Hermes Kanban（任务板）原生链路，形成 task（任务）、profile（配置身份）、worker run（工作者运行）、产物、Gate（门禁）闭环。

## 事实源

- Kanban board：`legal-cases`
- 流程文件：`/Users/appleoppa/.hermes/workspace/workflows/法律办案_Hermes-Kanban链路.md`
- 标准文件：`/Users/appleoppa/.hermes/workspace/standards/case-flow/苹果中枢办案流程协同标准_V7.2.md`
- task body 模板：`/Users/appleoppa/.hermes/workspace/templates/kanban/V72_KANBAN_TASK_BODY_TEMPLATE.md`
- handoff 模板：`/Users/appleoppa/.hermes/workspace/templates/kanban/V72_HANDOFF_METADATA_TEMPLATE.json`
- 案件初始化脚本：`/Users/appleoppa/.hermes/workspace/scripts/create_v72_kanban_case.py`

## 默认流程

```text
编号建档
→ 标准任务包/项目计划卡
→ 证据快筛
→ 并行初评
→ 差异合并
→ 二修
→ 律法复核
→ 巡视预审
→ 交付前整合
→ 巡视终审
→ 审计门禁
→ 归档
→ 交付
```

证据快筛通过后必须并行初评：主办部门、律法支持部、案件推演部、智脑知识部同时进入；不得回退为旧串行链路。

## 每个部门产物必须绑定

```text
Kanban Task ID:
Assignee Profile:
Worker Run ID:
Input Files:
Output Files:
Gate:
```

并附 `handoff_metadata` JSON。没有 `task_runs` / `worker_run_id` 时，只能说“已建任务/未运行”，不能说“部门 worker 已完成”。

## 初始化命令模式

正式案件需用本地 helper 创建 task graph：

```text
/Users/appleoppa/.hermes/workspace/scripts/create_v72_kanban_case.py --case-id PGG-YYYYMMDD-001 --case-name 案件名称 --lead-profile pgg-minshi
```

注意：没有真实案件信息时，只能创建/检查模板或 blocked 占位 task；不得把模板 task 说成正式案件执行。

## 模型口径

- 办案业务/支持部门默认：`deepseek-v4-flash`
- 巡视组、审计组默认：`gpt-5.5`
- `deepseekv4` profile 删除不等于 `custom:deepseek_v4_flash` provider 禁用。

## Pitfalls

- `--initial-status blocked` 的模板 task 可能被 dispatcher 误 promoted/claimed；如发生，立即 block 并核查 `hermes kanban runs <task_id>`，不要让模板任务继续消耗 token。
- P0 门禁不是“文件存在”，而是 task graph + worker run + output + Gate 的完整证据链。
