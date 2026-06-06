# 案件重编号示例：016→018

来源：2026-05-17 会话，用户反馈民邦案件编号冲突。

## 背景

- 民邦人力-雇主责任保险合同纠纷 案件在 2026-05-17 被重跑，当时目录混乱，错编为 016
- 016 已被德比时代-竞业限制-合同纠纷 占用（原始016）
- 正确编号应为 018（018-PGGMS-20260517-民邦人力-雇主责任保险合同纠纷）

## 涉及的系统范围

| 子系统 | 文件数 | 具体文件 |
|--------|--------|----------|
| 案件目录内部 | 12 | 预检报告、原始材料、分析报告、巡视报告、复核报告、格式校对稿、知识沉淀、自检报告、聚合交付报告、归档清单、meta.json |
| 审计队列 | 1 | audit-PGG-MS-20260517-{号}-shen-ji-*.json |
| 任务队列 | 1 | tasks.jsonl（含嵌套 JSON 的 _legacy 块） |
| 自检评分 | 1 | self_check_scores.json |
| 审计门禁记录 | 1 | audit_gate_records.json |
| 进化基因库 | 2 | auto-evolution-state.json, GENE-R65-C22R2-*.json |
| 技能引用 | 1 | skills/evolution-cycle/references/declared-capability-automation-gap-C22R1.md |
| 脚本示例 | 3 | scripts/knowledge_precipitator.py, audit_scanner.py, self_check_scorer.py |

## 特殊注意点

### tasks.jsonl 的 _legacy 字段
`_legacy` 块在 `input` 字段的 JSON 内部（双重嵌套），所以原始的116和016号是转义形式：
```
\"_legacy\": {\\\"审计编号\\\": \\\"AUDIT-20260517-016\\\", \\\"案件编号\\\": \\\"016-PGGMS-20260517\\\"}
```
需要用 `\\\"` 模式匹配，不能用普通文本替换。

### 脚本示例 vs 真实引用
knowledge_precipitator.py、audit_scanner.py、self_check_scorer.py 中的 016 是注释/帮助文本中的示例编号，不是对具体案件的引用。但为了一致性，也更新为 018。

### 目录重命名时机
建议在所有文件内容更新完成后再重命名目录，避免中间状态产生路径不一致。
