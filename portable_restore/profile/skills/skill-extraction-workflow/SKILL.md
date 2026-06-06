---
name: skill-extraction-workflow
description: 周期性技能萃取：扫描日志→识别模式→提案
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, workflow, maintenance, extraction, lifecycle]
    related_skills: [skill-creator, skill-vetter, hermes-agent-skill-authoring, session-logs-1.0.0]
---

# Skill Extraction Workflow — Compact

## Trigger

Use when extracting reusable skills from sessions, logs, failures, successful workflows or repeated user corrections.

## Workflow

1. Identify repeated/non-trivial pattern with future value.
2. Verify it worked or was user-corrected.
3. Write compact SKILL.md: trigger, workflow, pitfalls, verification.
4. Put long examples in references.
5. Validate skill loads and avoid saving stale task progress.

## Boundary

Memories store durable facts; procedures belong in skills; temporary outcomes belong in session logs/reports.

## Reference

Full extraction process archived at `references/full-skill-archive-20260601.md`.
