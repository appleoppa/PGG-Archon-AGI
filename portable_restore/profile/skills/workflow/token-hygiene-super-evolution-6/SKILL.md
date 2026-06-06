---
name: token-hygiene-super-evolution-6
description: 用坐标校正、截图裁剪、OCR优先、去噪压缩和流程门禁降低视觉/终端任务的 token 浪费与坐标误差。
version: 1.0.0
category: workflow
tags: [超级进化6, Token优化, 坐标校正, 25步净化]
created: 2026-05-25
updated: 2026-05-25
---

# Token Hygiene Super Evolution 6 — Compact

## Trigger

Use for token/context bloat, screenshot/OCR cost, coordinate correction, compression inefficiency, tool-output flooding, or long-task context hygiene.

## Core formulas

```text
X_real = X_out · (W_screen / W_img)
Y_real = Y_out · (H_screen / H_img)
Token_reserve = Token_text + Σ Token_img(n) for latest N<=3
Effort_valid = Total_effort - Waste_effort
APEX_MAX = Ω_A·β_bg·α_ack·Θ_TRI·∇K·ζσ·ηλ·EVM·A·B·TDHLGWB - ΣΔ_all
```

## Current context policy

- Prefer compact umbrella skill, then targeted reference.
- Raw outputs go to workspace; main context gets status/count/path/hash/blocker.
- Lean budget: default result 12000 chars, turn budget 30000, preview 500.
- Keep only latest necessary screenshots; OCR/text extraction before visual dumps.

## Pitfalls

- Compression requests can themselves explode if no global cap exists.
- Tool registry caps must not bypass config defaults.
- Screenshot scaling can mislead clicks without coordinate correction.

## Reference

Full historical implementation notes archived at `references/full-skill-archive-20260601.md`.
