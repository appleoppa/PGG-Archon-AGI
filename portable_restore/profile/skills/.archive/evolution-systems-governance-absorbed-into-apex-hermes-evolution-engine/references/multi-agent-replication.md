# Multi-Agent Replication — Absorbed Detail

Original skill: `multi-agent-replication`.

## Core Insight

Each sub-agent in an old system becomes a Hermes skill or a subsection of a class-level Hermes skill. The hub orchestrator skill owns dispatch logic. Data, rules, knowledge, and configuration are the real assets.

## Audit Source System

Catalog source files, agents, skills, config, knowledge, logs. For each sub-agent identify:

- role/purpose;
- rules/AGENTS content;
- identity/SOUL definition;
- memory/MEMORY index;
- owned skills/workflows;
- timeout/capabilities;
- hub dispatch algorithm.

## Mapping Template

Sub-agent SKILL.md should include role, rules, absolute prohibitions, dispatch instructions, input/output, knowledge paths, and original-system metadata where useful.

## Hub Template

Hub orchestrator should define quick-answer vs full-process paths, routing table, delegate_task templates, quality gates, and prohibitions against bypassing case management or self-executing specialist tasks.

## Verification

- Total file count source vs destination.
- Category-by-category counts.
- Critical files: SOUL/MEMORY/AGENTS/IDENTITY/HEARTBEAT/USER/CLAUDE where present.
- Path-mapped diff when directory names changed.
- Content integrity via size/hash spot checks.

## Pitfalls

- Do not just copy old framework files.
- Do not miss identity files.
- Do not skip secondary sub-agent skills.
- Do not assume one pass is enough.
- Do not embed secrets in SKILL.md.
