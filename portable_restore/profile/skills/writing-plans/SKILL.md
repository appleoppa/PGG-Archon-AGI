---
name: writing-plans
description: 从需求生成实施计划
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

# Writing Plans — Compact

## Trigger

Use when asked to turn a requirement into an implementation plan, project plan, legal work plan, or execution checklist.

## Workflow

1. Define objective, constraints, deliverables and risks.
2. Break work into phases with verification gates.
3. Identify dependencies, files/tools/owners and rollback.
4. Prefer actionable next steps over abstract strategy.
5. If execution is authorized and low-risk, act instead of only planning.

## Output

`goal`, `scope`, `steps`, `verification`, `risks`, `next_action`.

## Reference

Full planning templates archived at `references/full-skill-archive-20260601.md`.
