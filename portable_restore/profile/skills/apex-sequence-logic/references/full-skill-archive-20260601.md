---
name: apex-sequence-logic
description: APEX/开智三顺序逻辑：21354/12534/14325
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [apex, evolution, sequence, kaizhi]
    related_skills: [manual-evolution-loop, hermes-evolution]
---

# APEX 三顺序逻辑（当前版）

## 定位

APEX 三顺序是“开智进化循环”的代入方法，不是完成标准。当前开智本体只有：

```text
真实代入 → 短板自然暴露 → 外部开源/文档学习 → 吸收补齐 → 进化基因入库 → 验证
```

## 数字映射

| 数字 | 含义 | 动作要求 |
|---:|---|---|
| 1 | 融合 | 汇聚当前任务、经验、外部资料和候选增量 |
| 2 | 纠错 | 反证、查错、去幻觉，识别冲突和失真 |
| 3 | 降熵 | 压缩不确定性，分清证据等级、边界和优先级 |
| 4 | 规划 | 形成可执行路径、门禁、资源和收束方式 |
| 5 | 固化 | 把已验证增量写入记忆、技能、规范、配置或基因库 |

## 三种顺序

| 顺序 | 名称 | 用途 |
|---|---|---|
| 21354 | 审错优先 | 高风险、历史冲突、事实/法律/配置核验 |
| 12534 | 融合固化 | 新知识学习、外部来源吸收、技能沉淀 |
| 14325 | 规划反证 | 系统设计、cron/无人值守、复杂任务收束 |

### 实际落地案例（2026-05-31 终极进化公式）

| Phase | 顺序 | 实际动作 |
|-------|------|---------|
| Phase3 ARS Cycle | 21354 | 审边界（sidecar 不改 run_agent.py）→ 纠错（去重逻辑）→ 降熵（score≥75 gate）→ 规划（next_actions）→ 固化（写入 PGG DB） |
| Phase4 Trend Replay | 14325 | 规划（replay 架构）→ 压缩（semantic fingerprint）→ 回放（duplicate_gene_count）→ 仲裁（risk=stable/watch）→ 固化（dedup_gate） |
| Phase5 Promotion Gate | 12534 | 融合（Phase3+Phase4+多模型审查）→ 压缩（7项门禁）→ 固化（promotion_ready/held）→ 归档（state_surface）→ 验证（DB 读回） |

| Phase6 SE20 Force-Inherit | 12534 | 融合（SE20公式骨架+Gene339已有闭环）→降熵（区分可落地/不可落地成分）→固化（可落地成分写入 defect-map）→归档（Skill patch 完成）→验证（文件读回） | 8条中lim_{n→∞}、优先级高于原生参数等超出Hermes边界，已排除 | 超级进化20 SE20成分已映射至 apex-defect-repair-knowledge-map.md | ✅ defect-map 已更新 |

## 使用规则

- 每一步必须产生判断、证据、修复或沉淀。
- 不得只写编号、标题或空泛解释。
- 三顺序用于帮助暴露短板和组织补齐动作。
- 开智完成仍必须通过“短板→学习→补齐→入库→验证”门禁。

## 输出模板

| 字段 | 内容 |
|---|---|
| 选用顺序 | 21354 / 12534 / 14325 |
| 实际动作 | 每个数字对应的真实动作 |
| 暴露短板 | 从代入中自然出现的问题 |
| 外部学习 | 读取的来源和吸收点 |
| 固化结果 | 补齐动作、技能/规范/基因库写入 |
| 边界 | 未验证或不可夸大的部分 |
