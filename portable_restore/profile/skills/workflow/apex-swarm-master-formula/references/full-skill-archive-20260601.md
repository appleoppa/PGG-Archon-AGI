---
name: apex-swarm-master-formula
description: 超级进化15 蜂群Agent StraTA-APEX 主公式。单指令→策略生成→多Agent并行→分层优化→记忆同步→自验证闭环。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [apex, swarm, strategy, grpo, memllm, delegate, self-validation]
    related_skills: [apex-hermes-evolution-engine, hermes-evolution, manual-evolution-loop]
---

# APEX 蜂群主公式 — StraTA 技能

## 核心公式

```
ApexStraTA = π(z|s₁) ⊗ π(aₜ|z, sₜ) ⊗ GRPO(z, aₜ) ⊗ MemLLM
```

| 组件 | 符号 | Hermes 映射 | 状态 |
|---|---|---|---|
| GPT 全局策略生成 | z ~ π(s₁) | `full_toolcall_integration.plan()` + `qr route` | ✅ 已落地 |
| 固定策略并行执行 | aₜ ~ π(z, sₜ) | `delegate_task` batch 模式 | ✅ 已落地 |
| GRPO 分层优化 | GRPO = J(θ) = E[ΣA(z)+ΣA(aₜ)−βDKL] | `tools/grpo_lite_tool.py` 组评分+相对优势+KL-like惩罚 | ✅ GRPO-lite 已落地 |
| 长期记忆同步 | MemLLM = RAG + LongTermMem | memory_tool + hippocampus + gene DB | ⚠️ 需增强 |
| 最远点采样多样性 | tools/farthest_point_sampling.py | ✅ 已落地 |
| 自验证偏离约束 | tools/swarm_validation_gate_tool.py (deviation) | ✅ 已落地 |
| 主公式最终验证 | tools/swarm_validation_gate_tool.py (verify + heal) | ✅ 已落地 |
| MemLLM 统一管道 | tools/memllm_pipeline.py | ✅ 已落地 |

## 工作流

### Step 1: π(z|s₁) — 全局策略生成

收到复杂任务后，用 GPT（或主模型）生成结构化策略：

```text
输入: 用户任务描述（s₁）
输出: 结构化策略 z = {goal, subgoals, agent_specs, dependencies, verification_points}
工具: full_toolcall_plan / qr route → delegate_task
```

### Step 2: π(aₜ|z, sₜ) — 蜂群并行执行

用 delegate_task 批量派发 subagents，每个 agent 搭载独立的记忆上下文：

```text
输入: 策略 z
执行: delegate_task(tasks=[...], context=z)
输出: 各 agent 独立结果
```

### Step 3: GRPO(z, aₜ) — 分层优化

对 agent 执行结果进行组相对优化评分：

```text
组优势 A(z) = (z_result - group_mean) / group_std
组优势 A(aₜ) = (aₜ_result - group_mean) / group_std
KL 散度 DKL(π_new || π_old)
损失 J = avg(A(z) + A(aₜ)) - β × DKL
```

### Step 4: MemLLM — 记忆同步

每次蜂群执行后，回收各 agent 的记忆，同步到长期存储：

```text
1. RAG 检索相关上下文
2. 合并 agent 经验
3. 写入 MEMORY.md / USER.md / 基因库
4. 下一次轮次前自动 prefetch
```

### Step 5: 主公式验证闭环

任务声称完成前，代入主公式逐项检查：

```text
π(z|s₁): 原始策略是否覆盖？     ✅/❌
π(aₜ|z,sₜ): 执行是否匹配策略？  ✅/❌
GRPO: 优化是否执行？             ✅/❌
MemLLM: 记忆是否同步？            ✅/❌
未达标项 → 标记 + 启动自愈循环 → 重跑 → 再验证
全部达标 → 标记为完整完成
```

## 触发条件

```text
触发词: 蜂群, swarm, StraTA, 主公式, 超级进化15
自动触发: 涉及 ≥3 个子任务、多部门协作、长周期复杂任务
```

## 风险边界

| 边界 | 规则 |
|---|---|
| 策略不可覆盖全部细节 | π(z|s₁) 只出概要，具体执行由 subagent 自主裁量 |
| 最多 3 个并发 subagent | delegate_task 当前限制 |
| 自愈最多 3 轮 | 超 3 轮未达标则人工介入 |
| 不虚构 GRPO | GRPO 是简化版（无真实组采样和梯度），不能和 DeepSeek-R1 的 GRPO 训练混淆 |
| MemLLM 不虚构语义检索 | 使用现有 hippocampus + memory_tool 通路，不宣称 embedding/RAG 已底层实现 |
