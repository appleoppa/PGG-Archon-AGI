# External Learning: LLM Agent Skill/Tool Calling Decision Bias

**Source**: Edison Tech Blog — edison-a-n.github.io (2026-04-14)
**URL**: https://edison-a-n.github.io/2026/04/14/llm-tool-calling-decision-bias/
**Discovery context**: batch2第2轮开智进化循环, W3(技能利用率62%)短板外部学习

## Core Finding

LLM agents with tools and skills have a **systemic decision bias** against calling tools/skills. This is not a bug in any specific framework — it's an inherent characteristic of LLM training paradigms.

## Three Root Cause Layers

| Layer | Issue |
|-------|-------|
| 4.1 Training (RLHF) | Implicit "if I can answer, don't call tools" bias from RLHF training data |
| 4.2 Architecture (Progressive Disclosure) | Two-stage skill loading (description → read_file) delegates the load decision entirely to the LLM |
| 4.3 Information | All tools pre-loaded in context → LLM thinks "I already have everything I need" |

## Three Solution Categories (applicable to Hermes)

| Solution | How it works | Applicability |
|----------|-------------|---------------|
| 1. Deterministic Injection | Pre-load critical skill content directly into system prompt (bypass LLM decision) | Best for cron/evolution: actively load known-needed skills before starting the task |
| 2. Dedicated Skill-Loading Tool | Create a semantically distinct tool like `load_skill(name)` vs generic `read_file` | Hermes already has `skill_view()` — semantically distinct |
| 3. Pre-Completion Checklist | Force-check before responding whether required skills were loaded | Applicable in structured workflows (cron evolution) |

## Implication for Hermes

- Description-based triggering (skill description matching) is inherently uncertain
- In cron/evolution mode, actively load zero-use skills instead of waiting for description matching
- The manual-evolution-loop §9.5 skill utilization tracking is directionally correct
- Legal skills (apple-*, dept-*) are a structural limitation, not a quality defect — they need real case work to activate
