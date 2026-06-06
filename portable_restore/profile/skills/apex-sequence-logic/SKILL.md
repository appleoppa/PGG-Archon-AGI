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

# APEX Sequence Logic — Compact

## Trigger

Use for choosing APEX/开智 execution order: 21354, 12534 or 14325.

## Selection

- `21354`: audit/error-first when hallucination or risk is suspected.
- `12534`: absorb/fuse/solidify when input is reliable and implementation is clear.
- `14325`: plan/refute when architecture risk or ambiguity is high.

## Rule

Sequence numbers are not decoration; each step must produce evidence, repair, verification or durable learning.

## Upstream absorption / multi-LLM repair pattern

For APEX/PGG upstream-update absorption tasks with dirty local changes, use `21354` first: audit local/upstream divergence and hallucination risk before writing code. Then switch to `12534` only after evidence is stable: absorb P0/P1/P2 fixes, fuse with local hardening, solidify via tests, and archive the result. If the user says “调用所有 LLM / 代入公式 / 不造假”, treat role-play as invalid: make real provider calls, record status/output paths, and do not claim a model participated when credentials or API calls failed.

## Sequential activation discipline (2026-06-02)

For external APEX / PGG / AGI component activation, especially after the user reports lag or simulation risk, use strict one-by-one activation:

1. audit: inspect code, hardcoded scores, mocks, I/O, daemon/port side effects.
2. smoke/simulate: run a bounded dry smoke test that does not start long-lived services.
3. activate one component only.
4. debug until smooth: fix import, cache, AST, pycache, resource-limit and schema errors.
5. verify: focused tests + full health + relevant daemon/process check.
6. commit only current-theme files.
7. continue to the next component only when the previous component is clean.

Never batch-unlock several components when the system is already lagging. Health/check scanners must skip `__pycache__`, caches, huge directories and binary files, and must enforce bounded file limits.

## Auto-Fix integration (2026-06-01)

When using `SequenceStateMachine` from `agent/apex_runtimeos_sequence.py`, the `auto_fix_step(command)` method combines step execution with AutoFixEngine closed-loop:

- Steps through the sequence
- Runs command through AutoFixEngine (execute → score → fix → re-verify up to 3 times)
- Records fix attempts as step evidence
- Updates the evidence ledger with real score

Best used in "repair" steps (21354 sequence) or any step requiring external command execution.

Example: `sm = SequenceStateMachine("21354", "Repair build"); result = sm.auto_fix_step("cargo build")`

Also see: `agent/auto_fix.py` — AutoFixEngine class with 8 heuristic fixers (pip install, mkdir, kill port, etc.)

## Reference

Full sequence examples archived at `references/full-skill-archive-20260601.md`.
