---
name: apex-skill
description: APEX-SKILL v0.1.1 — Released — PGG Archon APEX 主公式 skill 释放层
version: 0.1.1
author: Apple Didi (苹果弟弟)
license: MIT
metadata:
  hermes:
    tags: [apex, super-evolution-23, pgg-archon, skill-releasing]
    related_skills: [apex-sequence-logic, pgg-archon-runtime, super-evolution-15, super-evolution-20]
---

# APEX-SKILL v0.1.1 — Released

> 编号：超级进化23
> 主题：APEX-SKILL 释放层
> 状态：v0.1.1 SKILL 包装（bound）
> 边界：内部 skill 释放规范，不是 full AGI

## 0. 用途

本 skill 是 APEX 主公式（终极进化公式、ΔG 演化范式、CMMI 工业化标准等）的统一释放入口。  
当一个 APEX 主公式要被实际调用时，应该先检查本 skill 是否能直接释放，避免重复造轮子。

## 1. 释放层定义

| 层级 | 名称 | 作用 |
|---|---|---|
| L0 | axiom | 不可分公式，例如 CMMI 5 级、终极进化公式本体 |
| L1 | main | 主公式，例如 ΔG 演化范式、AGI_Global=lim(...) |
| L2 | composite | 复合 skill，由 L0+L1 组合，例如 apex-book-to-skill |
| L3 | adapter | 适配 skill，把 L1/L2 接到具体场景，例如本机 Rust fused-watcher |

## 2. 释放时必填字段

- `name`
- `version`（semver 严格）
- `description`（≤200 字）
- `triggers`（最小触发条件 1–3 条）
- `evidence_required`（至少 1 项可读证据：测试、HTTP、commit、readback）

## 3. 释放失败信号

- 描述为空
- 没有触发条件
- 没有任何 evidence_required
- 直接调用 GPT/Claude/DeepSeek 而没有可读 backup

## 4. 落地清单

- [x] SKILL.md 包装（v0.1.1, 2026-06-04）
- [ ] 单元测试（apex_skill_loaders_test.py）
- [ ] 释放日志（apex_skill_releases.jsonl）
- [ ] 反查 33 个超级进化文件是否完整覆盖 L0–L3

## 5. 关联入口

- 关联 skill：`apex-sequence-logic` / `pgg-archon-runtime` / `super-evolution-15`
- 文件位置：`~/.hermes/skills/workflow/apex-skill/`
- 总账：`~/.hermes/data/EVOLUTION_MANIFEST.json`（latest_p2_20260604）
