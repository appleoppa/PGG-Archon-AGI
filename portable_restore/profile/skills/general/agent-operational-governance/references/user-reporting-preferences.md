# User Reporting Preferences — Absorbed Detail

Original skill: `user-reporting-preferences`.

## Style

- 中文、简洁、直接。
- 默认表格：状态 / 数据 / 证据 / 下一步。
- Feishu/mobile 避免密集堆叠表格，改用层级清晰的字段块。
- 用户指出格式乱或不好看时，立刻切换更清爽布局。
- 避免命令/path/tool 细节，除非作为必要证据。
- 本地路径不要宣称可点击；不可点击时改成 plain path/code block。
- token/context 是用户资源；进度类问题只给关键字段，除非要求细节。
- 绝不从 artifact、status file、partial run 暗示完成。

## Five Principles

| Principle | Output |
|---|---|
| 目标明确化 | 目标、验收、边界 |
| 流程标准化 | 步骤、状态、门禁 |
| 责任具体化 | 谁/哪个部门/哪个系统负责 |
| 信息透明化 | 数据、证据等级、状态字段 |
| 资源配置最优化 | 资源、理由、替代方案 |

## Default Skeleton

| 项目 | 内容 |
|---|---|
| 当前状态 | 未开始/执行中/部分完成/完成/证据不足 |
| 核心数据 | 数量、比例、前后变化 |
| 证据等级 | 已核验/部分核验/未核验 |
| 风险边界 | 不能夸大的部分 |
| 下一步 | 如果未完成，下一步动作 |

## Quality Gate

- Exact status?
- Data and evidence visible?
- Completion boundary clear?
- Short but not empty?
