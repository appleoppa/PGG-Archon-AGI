---
name: hermes-agent-skill-authoring
description: 编写SKILL.md：frontmatter、校验、结构
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, authoring, hermes-agent, conventions, skill-md]
    related_skills: [writing-plans, requesting-code-review]
---

# Hermes Agent Skill Authoring — Compact

## Trigger

Use when creating, editing, compacting, archiving, validating, or troubleshooting SKILL.md files.

## Good skill shape

- YAML frontmatter with name/description/version/tags.
- Clear trigger conditions.
- Minimal workflow steps.
- Pitfalls and boundaries.
- Verification/output contract.
- Long examples in `references/`, not main `SKILL.md`.

## Compacting rule

Archive full old content first, then keep main skill under the smallest useful size. The main skill should tell when to load references.

## Reference

Full authoring guide archived at `references/full-skill-archive-20260601.md`.
