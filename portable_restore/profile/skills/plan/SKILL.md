---
name: plan
description: 计划模式：写Markdown计划到.hermes/plans/
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, implementation, workflow]
    related_skills: [writing-plans, subagent-driven-development]
---

# Plan Mode — Compact

## Trigger

Use when user explicitly asks for plan mode or a Markdown implementation plan saved under `.hermes/plans/`.

## Workflow

1. Define objective, scope and constraints.
2. Break into verifiable tasks.
3. Include risks, rollback and test gates.
4. Save plan to the requested/standard path.
5. Verify file exists and report path.

## Reference

Full plan format archived at `references/full-skill-archive-20260601.md`.
