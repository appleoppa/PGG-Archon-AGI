---
name: subagent-driven-development
description: 通过delegate_task子智能体执行计划
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development]
---

# Subagent Driven Development — Compact

## Trigger

Use when work benefits from parallel research, independent review, isolated coding, or large context reduction through delegate_task.

## Rules

- Pass full context; subagents have no memory.
- Use subagents for independent reasoning/research/review, not for tasks requiring user interaction.
- Verify subagent claims with file readback, tests, URLs, IDs, or diffs.
- Do not use subagent role names to fake GPT/Claude/model calls.

## Workflow

1. Split into independent tasks.
2. Delegate with exact paths/constraints/output schema.
3. Receive summaries.
4. Verify any side effect yourself.
5. Integrate and report.

## Reference

Full prompt patterns archived at `references/full-skill-archive-20260601.md`.
