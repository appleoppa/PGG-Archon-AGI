---
name: evolution-systems-governance
description: 开智/EVM/多智能体进化系统治理总纲：三顺序循环、EVM缺陷治理、河图洛书路由、GitHub工厂、多智能体技能复制与真实任务迁移
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [evolution, evm, router, multi-agent, governance, github-factory]
    related_skills: [manual-evolution-loop, evm-integration, multi-agent-replication]
---

# Evolution Systems Governance

## Overview

这是面向“开智进化循环 + EVM治理 + 河图洛书路由 + GitHub工厂 + 多智能体迁移/复制”的伞形技能。它把原本分散在多个窄技能中的流程合并为一个 class-level 入口：

- 用现行开智规范驱动真实进化闭环；
- 用 EVM 暴露和治理缺陷；
- 用多模型路由/反证仲裁提升可靠性；
- 用 GitHub/外部学习作为反幻觉外脑；
- 用 SKILL.md + delegate_task 复制多智能体体系，而不是复制旧框架本身。

## When to Use

- 用户要求执行、重跑、审计、修复“开智进化循环”。
- 用户提到 EVM、河图洛书路由、超级路由、GitHub factory、进化基因库。
- 用户要求把外部/旧多智能体系统迁移为 Hermes skills。
- 任务涉及自我进化、技能沉淀、短板暴露、真实任务迁移。
- 需要判断是否调用多模型链、外部学习、反证仲裁。

## 1. Current Evolution Loop Standard

唯一现行标准以工作空间当前规范为准；旧 cron、旧状态机、旧 R1-R5、旧五回合材料只能作为复盘资料，不能覆盖现行规范。

核心闭环：

```text
公式审错与修复 → 21354/12534/14325 各5遍 → 短板自然暴露 → EVM缺陷治理 → 超级路由决策 → GitHub/开源/官方文档学习 → 河图洛书/多模型反证仲裁 → 吸收补齐 → EVM回测 → 进化基因入库 → 验证 → 自驱报告与真实任务迁移
```

### Entry Prerequisite Gate

真实任务开始前先识别任务类型和强制触发技能；若多个入口并列，先执行任务前必须动作并记录证据字段。开智任务最低顺序：

1. 加载进化治理技能；
2. 读取现行规范；
3. 判断是否命中 quantum-channel-router；
4. 命中则先 route；
5. 再进入任务本体。

## 2. APEX Three-Sequence Logic

- **21354**：审错优先，用于事实核验、历史冲突、幻觉风险。
- **12534**：融合固化，用于吸收新知、沉淀技能、形成规则。
- **14325**：规划反证，用于复杂项目、cron/无人值守、执行路径压力测试。

三种顺序必须真实代入，每一步产生判断、证据、修复或沉淀；不能只写编号。

## 3. EVM Defect Governance

### Formula

```text
EVM = E × V × M × A × Base × 7古法 × (1 - defect_rate(含短板惩罚))
```

关键规则：

- 古法因子只乘 7 项，不额外乘八卦。
- 缺陷率使用平均缺陷 + 最大短板惩罚，而不是简单平均。
- 古法增强使用软上限；boost 系数可配置。

### Defect Mapping

| Defect | Ancient governance lens |
|---|---|
| ΔMem / ΔSoul | 黄帝内经 |
| ΔErr / ΔTok | 道德经 |
| ΔAgt / ΔRun | 易经 |
| ΔPan / ΔClw | 河图洛书 |
| ΔPrm / ΔNet | 天干地支 |
| ΔRes / ΔLog | 五行 |

### Route Necessity Gate

不要把所有任务默认送入多模型链。先判断复杂度、风险和不确定性：

- 低风险简单任务：主模型直接处理。
- 高风险、事实密集、法律、配置、进化、系统修复任务：进入路由/反证链。

## 4. 河图洛书 / Super Router Integration

典型五阶段链：

| Step | Role | Model class |
|---|---|---|
| 1 | 主脑统筹 | GPT 系主模型 |
| 2 | 反证审错 | DeepSeek/强审错模型 |
| 3 | 修复落地 | MiniMax/执行模型 |
| 4 | 旁证压缩 | GLM/压缩模型 |
| 5 | 主脑收束 | GPT 系主模型 |

### Provider Pitfalls

- 5yuantoken 中文乱码时用 `json.loads(resp.content)`，不要用 `resp.json()`。
- MiniMax anthropic mode base URL 是 `https://api.minimaxi.com/anthropic`，最终 endpoint 为 `/anthropic/v1/messages`。
- DeepSeek base URL 不带 `/v1` 时才匹配其 chat/completions 路径。
- HTTP 200 不等于有效输出；必须检查非空用户可见文本、结论、证据、缺陷或修复内容。
- provider 密钥通常在 `.env`，Python 子进程要显式加载或使用项目 loader。

## 5. GitHub Factory / External Brain

GitHub factory 和外部学习用于给进化循环提供外部反馈，不是写报告装饰：

- 外部来源必须在短板暴露之后读取；
- 来源必须改变补齐动作；
- 反证仲裁必须产生修正增量；
- 结果需要落入规则、技能、数据库、配置或真实任务迁移。

## 6. Multi-Agent Replication Pattern

复制多智能体系统时，价值在数据、规则、知识和配置，不在旧框架。

### Three Layers

1. Hub Orchestrator SKILL.md：统一入口，负责路由和质量门禁。
2. Sub-agent SKILL.md：每个角色的职责、规则、输入输出和知识路径。
3. Data/Knowledge/Config：放入 workspace 或 migration，SKILL.md 只引用，不嵌入密钥。

### Migration Flow

1. 全量盘点源系统文件和角色。
2. 提取每个 sub-agent 的 role / rules / identity / memory / workflows。
3. 为每个角色写 class-level skill 或归入已有部门伞形 skill。
4. 建 hub 的路由表和 delegate_task 模板。
5. 多轮 gap analysis：文件数、类别数、关键文件、路径映射、内容大小/哈希抽样。

## 7. Completion Gates

开智/进化类任务必须同时满足：

- 短板来自真实代入或真实失败；
- 外部学习发生在短板之后；
- 学习改变补齐动作；
- 补齐已落地到规则/技能/流程/配置/数据库；
- 进化基因或等效记录已入库并读回验证；
- EVM/路由/反证环节有有效输出；
- 自驱报告和真实任务迁移已生成；
- 不从 exit_code、日志存在或状态字段单独推断完成。

## 8. References

- `references/manual-evolution-loop.md`：现行开智循环门禁、三顺序、已知陷阱。
- `references/evm-integration.md`：EVM formula、provider quirks、router/GitHub factory 集成细节。
- `references/multi-agent-replication.md`：多智能体系统迁移为 Hermes skills 的具体模板。

## Verification Checklist

- [ ] 是否读取并服从现行规范，而不是旧状态机？
- [ ] 是否真实执行三顺序代入，而不是只写编号？
- [ ] 短板是否自然暴露，有证据来源？
- [ ] 是否进入 EVM/路由/外部学习/反证，且输出有效？
- [ ] 补齐是否实际落地，而非只写分析？
- [ ] 基因/记录是否写入后读回验证？
- [ ] 多智能体迁移是否优先保留数据、规则、知识、配置？
