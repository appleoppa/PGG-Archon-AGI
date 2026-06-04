---
name: pgg-archon-closed-loop-formula
description: PGG Archon / Apple Didi 苹果中枢 流程闭合总公式 — 真实代入 → 短板暴露 → 外部学习 → 吸收补齐 → 进化基因入库 → 验证
version: 0.1.0
author: Apple Didi (苹果弟弟)
license: MIT
metadata:
  hermes:
    tags: [pgg-archon, closed-loop, total-formula, super-evolution-27]
    related_skills: [apex-sequence-logic, pgg-archon-runtime, super-evolution-20, agentic-rl-five-layer]
---

# PGG Archon 苹果中枢 流程闭合总公式

> 编号：超级进化27
> 主题：流程闭合总公式
> 状态：v0.1.0 SKILL 固化（bound）
> 边界：内部工程规范，不是 full AGI，不是外部评测

## 0. 触发条件

Use when the user asks to:

- "全量闭环"、"一次性推进"、"继续"、"流程闭合"
- 需要把"做事 → 验证 → 入库 → 再做事"压成一条主线
- 需要在多人多模型场景下强制门禁与追溯

## 1. 总公式（六阶闭合）

```
R[0] = 真实代入
R[1] = 短板暴露 (gap_detect)
R[2] = 外部学习 (LDR 检索 + GitHub/vx 开源)
R[3] = 吸收补齐 (code_self_fix)
R[4] = 进化基因入库 (GeneDB candidate → promotion)
R[5] = 验证 (readback + test + 6-model LLM verify)
close  = R[5] → R[0]  (回到真实代入)
```

每一阶都产生判断、证据、修复或沉淀；不允许"写编号不算事"。

## 2. 强制门禁

- 门禁0 真实代入：必须存在可读文件、命令输出、HTTP 状态码、测试结果之一作为 evidence。
- 门禁1 短板暴露：必须列出 ≥1 个具体缺口（不是泛泛的"需要优化"）。
- 门禁2 外部学习：缺知识时调用 LDR（本地 deep research）检索 + GitHub/vx/arxiv 等开源。
- 门禁3 吸收补齐：写出可回滚的代码/配置/数据修改，写明 backup + readback。
- 门禁4 基因入库：candidate 必须经全候选只读 gate → 独立 LLM quorum → per-gene transaction；禁止批量自动晋升。
- 门禁5 验证：≥2 路 LLM 可见 verdict；测试 passed；commit hash；manifest 读回。

## 3. 闭环状态机

```
未开始 → 执行中 → 部分完成（evidence 不足）
                    ↓
                  完整完成（5/5 门禁过）
                    ↓
                基因已固化（gene_db.promoted=1）
                    ↓
                  回到真实代入（新问题）
```

## 4. 与 APEX 三顺序逻辑的关系

- 21354 审错优先型 → 门禁 1 + 5
- 12534 融合固化型 → 门禁 2 + 3 + 4
- 14325 规划反证型 → 门禁 0 → 1 → 5 整体节奏

## 5. 错误信号（出现则说明闭环破裂）

- 文件存在就声称完成
- 服务启动就声称能力可用
- LLM 未真实调用就声称多模型共识
- 未做 readback 就声称 DB 修改完成
- 修复未带 backup + rollback 就直接执行

## 6. 输出模板

```text
状态：未开始 / 执行中 / 部分完成 / 完整完成
已核验：进程 / launchd / 端口 / 目录 / 日志 / 状态卡
证据：HTTP 200 / test N passed / commit hash / sha256
回滚：command/path
边界：内部工程 / 不宣称 full AGI / 不宣称外部评测
```

## 7. 关联入口

- 真实总账：`~/.hermes/data/EVOLUTION_MANIFEST.json`
- GeneDB：`~/.hermes/data/pgg_archon.db`
- 代码：`~/.hermes/hermes-agent/agent/pgg_archon_*.py`
- 治理：`~/.hermes/workspace/治理/`
- 审计：`~/.hermes/workspace/audit/`
