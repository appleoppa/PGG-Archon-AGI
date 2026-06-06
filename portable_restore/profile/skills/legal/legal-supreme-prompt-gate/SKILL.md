---
name: legal-supreme-prompt-gate
description: 法律 Supreme Prompt 真实性门禁：把全能/零风险法律AGI口号转化为可验证法律服务目标与办案清单
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [legal, agi, truthfulness, gate, pgg-archon]
---

# Legal Supreme Prompt Gate — Compact

## Trigger

Use when legal prompts/claims imply all-powerful legal AGI, zero-risk legal analysis, complete automation, or unbounded legal capability.

## Gate

Transform slogans into verifiable legal service objectives:

- jurisdiction and facts;
- issue list;
- applicable law/cases;
- evidence and burden;
- risk and uncertainty;
- human lawyer review boundary;
- deliverable format.

## Forbidden

Do not claim full legal AGI, zero退件/zero败诉, replacement of lawyer, official certification, or unsupervised production takeover.

## Semi-external legal taskset runner gate

When building or reviewing a legal taskset / benchmark-like runner:

- Reserve MiMo / `mimo_v25_pro_auditor` for third-party judging only; do not include it in ordinary legal-processing provider pools.
- Default ordinary legal providers should be explicit and bounded; explicit MiMo requests must fail closed rather than silently run.
- Do not call process-safety smoke results `LegalBench`, `LexGLUE`, legal correctness proof, court-ready output, or AGI-level evidence.
- Summary pass rates must require both successful provider response and positive deterministic score; timeout, HTTP failure, empty output, local-only precheck, or scorer-only marker hits cannot count as pass.
- Clamp timeout / worker count / provider count before execution, and record the clamp values in summaries.
- Legal prompts must include evidence-first gates: no fabricated facts/statutes/cases/courts/docket numbers; missing facts become 材料不足/待补; jurisdiction and claim-amount domains require dedicated checklists.

Session detail: `references/p5-legal-task-runner-gate-20260606.md`.

## Reference

Full gate patterns archived at `references/full-skill-archive-20260601.md`.
