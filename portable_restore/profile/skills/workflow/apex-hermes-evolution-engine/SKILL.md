---
name: apex-hermes-evolution-engine
description: Compact APEX/Hermes evolution engine: turn real task traces, long context, search results and subagent findings into verified reusable skills/genes without fabricating API calls, background evolution, or AGI completion.
version: 1.1.0
compact_rewrite: 2026-06-01
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [apex, evolution, skills, memory, context, trajectory, subagents]
    related_skills: [manual-evolution-loop, hermes-evolution, search-skillbank, subagent-driven-development, file-system-management, token-hygiene-super-evolution-6]
---

# APEX Hermes Evolution Engine — Compact

## Trigger

Use this skill when the task involves:

- learning complex materials and turning them into reusable procedures;
- improving Hermes / PGG Archon workflows;
- extracting skills, genes, rules or reports from real task traces;
- context-heavy audits, long search results, subagent findings or evolution loops.

Do **not** use it for simple Q&A, small edits, unverified AGI claims, or requests to bypass safety/core authorization.

## Core loop

```text
Select → Read targeted evidence → Act with tools/subagents → Review with tests/readback → Evolve into skill/gene/report
```

Meaning:

1. **Select**: choose the minimum relevant skill/tool/model route. Do not load multiple large skills by default.
2. **Read**: use search, line windows, DB counts and hashes before full documents.
3. **Act**: execute low-risk reversible improvements; delegate only when it reduces context or parallelizes real work.
4. **Review**: verify with tests, readback, hashes, DB rows, or actual tool output.
5. **Evolve**: save durable procedures into skills/genes only after real verification.

## Context discipline

Follow Super Evolution 21 / APEX_MAX context policy:

```text
APEX_MAX = Ω_A·β_bg·α_ack·Θ_TRI·∇K·ζσ·ηλ·EVM·A·B·TDHLGWB - ΣΔ_all
```

Engineering interpretation:

- `∇K`: find the smallest knowledge slice that changes action.
- `ζσ`: persist raw logs to workspace; return only summary/path/hash/blockers.
- `ηλ`: reduce latency by avoiding large tool dumps and avoidable compression calls.
- `ΣΔ_all`: subtract skill bloat, tool-output bloat, context pollution, logic fragmentation and accuracy loss.

Default for audits:

```text
raw output → workspace evidence file
main context → status + counts + path + sha256 + blockers + next action
```

## Evolution truth gates

A result can be called evolved only if all apply:

- shortcoming came from a real task/failure/audit;
- new material or formula changed an implemented rule;
- implementation landed in code/config/skill/GeneDB/report;
- tests or readback passed;
- boundaries are explicit.

Forbidden claims:

- full AGI completed;
- model weights or hidden reasoning modified;
- infinite background evolution running;
- GPT/Claude/MIMO participated without real provider call evidence;
- file existence alone equals capability.

## Multi-model / route rule

For AGI/evolution/architecture tasks:

- Prefer GPT/Claude real provider calls when the decision is high impact.
- If a provider fails, record the real failure; do not role-play it.
- Low-risk local engineering improvements may proceed with local tests and GeneDB readback.

## Output contract

Report in concise fields:

```text
状态:
改动:
证据:
测试:
GeneDB/Skill:
边界:
下一步:
```

## References

Full pre-compact version archived at:

- `references/full-skill-archive-20260601.md`

Read that archive only when an exact legacy phase detail is necessary. Do not load it for ordinary evolution/context work.
