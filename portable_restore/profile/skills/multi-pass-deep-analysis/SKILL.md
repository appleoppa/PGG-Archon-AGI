---
name: multi-pass-deep-analysis
description: 多轮次深度分析：解决单次分析深度浅问题
trigger_conditions:
  - 需要深度分析超过5个维度或5000行代码的复杂任务
  - 需要跨文件/跨版本历史推理的任务
  - 已知或有嫌疑存在层次较深的隐藏问题
  - 需要多角度交叉验证的场景
  - 首次分析后发现需要补审的场景
---

# Multi-Pass Deep Analysis — Compact

## Trigger

Use when single-pass analysis is likely shallow: complex legal/technical strategy, architecture review, contradiction resolution, or high-stakes synthesis.

## Pass structure

1. Problem framing and assumptions.
2. Evidence inventory and missing data.
3. First analysis.
4. Counter-analysis / failure modes.
5. Synthesis and decision.
6. Verification checklist and next action.

## Context discipline

Do not dump every pass into the user reply. Keep raw notes in workspace when long; final answer should show decision, evidence, uncertainty, and action.

## Reference

Full templates archived at `references/full-skill-archive-20260601.md`.
