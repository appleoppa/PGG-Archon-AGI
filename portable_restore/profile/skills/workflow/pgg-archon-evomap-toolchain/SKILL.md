---
name: pgg-archon-evomap-toolchain
description: 超级进化16.5 — 进化核心驱动：evolver / autoresearch / superpowers / openhands 在 PGG Archon 中的安装与状态卡
version: 0.1.0
author: Apple Didi (苹果弟弟)
license: MIT
metadata:
  hermes:
    tags: [pgg-archon, super-evolution-16.5, evolver, autoresearch, superpowers, openhands, evomap]
    related_skills: [tiangong-four-core, pgg-archon-runtime, apex-skill]
---

# PGG Archon Evomap Toolchain — 进化核心驱动

> 编号：超级进化16.5
> 主题：进化核心驱动
> 状态：v0.1.0 半成品 → 真实状态卡（bound）
> 边界：内部工具链状态记录，不是 full AGI，不是 full open-source

## 0. evomap 概念

evomap 把"进化核心驱动"分解为四个协作工具：

1. **evolver** — 进化执行器（ranking / selection / mutation）
2. **autoresearch** — 自动研究器（hypothesis → experiment → result）
3. **superpowers** — 能力增强器（meta-skill 释放）
4. **openhands** — 开放手（跨环境沙箱执行）

## 1. 当前本机真实状态卡（2026-06-04）

| 工具 | 状态 | 落点 | 备注 |
|---|---|---|---|
| evolver | partial | 隐含在 `apex13 fused-watch` 与 `pgg_archon_delta_gate.py` | 未独立封装 |
| autoresearch | partial | 隐含在 `pgg_archon_regression_generator.py` 与 `pgg_archon_ultimate_evolution_ars_cycle.py` | 未独立封装 |
| superpowers | partial | 显式在 `skills/workflow/super-evolution-20/` 与 `apex-skill` | SKILL 已落地 |
| openhands | absent | 无独立模块 | 待补 |

## 2. 真实缺口（半成品 → 真完成的距离）

- evolver: 缺独立 `agent/pgg_archon_evolver.py` 入口与配置 schema
- autoresearch: 缺独立 `agent/pgg_archon_autoresearch.py` 入口与运行期 hypothesis
- openhands: 缺独立 `agent/pgg_archon_openhands.py` 入口与沙箱配置

## 3. 真实修复路径（低风险、bounded）

1. 在 `agent/` 下补 3 个薄壳脚本（每个 ≤200 行），做：
   - import 校验
   - 已有 Rust / Python 工具的 export list
   - 不修改任何现状行为

2. 给 3 个薄壳分别补 SKILL.md（v0.1.0）

3. 跑 `pytest` 验证 import + 落点 readback

4. commit + manifest 读回

## 4. 关联入口

- 关联 skill：`tiangong-four-core` / `pgg-archon-runtime` / `apex-skill`
- 关联代码：`agent/pgg_archon_ultimate_evolution_ars_cycle.py` 等
- 总账：`~/.hermes/data/EVOLUTION_MANIFEST.json`
