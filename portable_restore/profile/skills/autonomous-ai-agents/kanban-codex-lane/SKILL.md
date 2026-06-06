---
name: kanban-codex-lane
description: Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane while Hermes keeps ownership of task lifecycle, reconciliation, testing, and handoff.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, codex, worktrees, autonomous-agents, prediction-market-bot]
    related_skills: [kanban-worker, codex, hermes-agent]
---

# Kanban Codex Lane — Compact

## Trigger

Use when a Hermes Kanban worker should run Codex CLI or another isolated coding agent for a lane/task.

## Workflow

1. Identify lane, repo, task scope, and allowed files.
2. Start isolated agent with explicit prompt and constraints.
3. Keep secrets out of prompts and logs.
4. Poll boundedly; capture output path/log.
5. Verify changes yourself with tests/diff before reporting.
6. Merge/apply only intended changes.

## Safety

Subagent/CLI self-reports are not proof. Require diff, test output, file readback, or artifact path. Do not let agent edit unrelated repos or persistent credentials.

## Output

`lane`, `task`, `agent`, `files_changed`, `tests`, `status`, `blockers`.

## Reference

Full lane prompts and examples archived at `references/full-skill-archive-20260601.md`.
