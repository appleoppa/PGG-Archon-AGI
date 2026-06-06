# V7.2 Hermes-Kanban Legal Case Execution Pattern

Use when the user says “开始办案 / 启动办案 / 执行办案 / 开案” or asks to upgrade the legal case workflow to Hermes 0.15.1 native multi-profile execution.

## Core rule

Formal cases must not remain only file-based department collaboration. They must enter a Kanban board with task/run evidence:

- Board: `legal-cases`
- Central profile: `default`
- Department profiles: `pgg-*`
- Required evidence: `task_id`, `assignee_profile`, `worker_run_id`, input/output files, Gate.

If a task exists but no `task_runs` entry exists, state “task created / worker not run yet”; do not claim department worker completion.

## Standard graph

1. `pgg-anguan`: 编号建档
2. `default`: 标准案件任务包 + 项目计划卡
3. `pgg-zhengju`: 证据门禁快筛
4. Parallel initial review after evidence Go/Conditional Go:
   - lead business department: 主办初评
   - `pgg-law`: 律法初核
   - `pgg-tuiyan`: 案件推演
   - `pgg-zhinao`: 智脑支持
5. `default`: 部门差异合并
6. lead business department: 二修 + 格式自检
7. `pgg-law`: 正式依据复核
8. `pgg-xunshi`: 轻量预审
9. `default`: 交付前整合
10. `pgg-xunshi`: 终审
11. `pgg-shenji`: 最终审计门禁
12. `pgg-anguan` + `pgg-zhinao`: 归档沉淀
13. `default`: 交付

## Required department output footer

```text
Kanban Task ID:
Assignee Profile:
Worker Run ID:
Input Files:
Output Files:
Gate:
```

Also keep the V7.2 seven-field handoff interface and attach `handoff_metadata` JSON.

## Model口径

Deleting a `deepseekv4` profile does not mean the DeepSeek provider is disabled. Current intended口径:

- Business/support departments: `deepseek-v4-flash` via `custom:deepseek_v4_flash`.
- Quality gate departments (`pgg-xunshi`, `pgg-shenji`): `gpt-5.5`.

## Pitfalls

- Do not create a template task in `ready` status; the dispatcher may claim it. Template/non-case tasks should be blocked or clearly marked non-executable.
- Do not treat a Markdown workflow file as execution evidence.
- Do not reintroduce a standalone 文书机要部; drafting/formatting belongs inside the lead business department self-check.
- If materials are missing, mark the relevant task blocked/Hold and generate a补证/整改 task rather than calling the case complete.
