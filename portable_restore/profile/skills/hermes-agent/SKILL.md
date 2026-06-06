---
name: hermes-agent
description: Hermes Agent配置、排障、使用手册
version: 2.2.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, cron, gateway, memory, skills]
    related_skills: [hermes-agent-skill-authoring]
---

# Hermes Agent — Compact

## Trigger

Use before answering or modifying Hermes Agent itself: CLI, config, providers, tools, skills, profiles, Web UI, gateway, voice, plugins, cron, memory or runtime.

Docs: https://hermes-agent.nousresearch.com/docs

## Core commands

Prefer official Hermes CLI/config tools where available. Inspect current profile/config before changing anything. Do not print secrets.

## Workflow

1. Identify active profile and scope: default vs named profile.
2. Read relevant config/tool/skill state with targeted commands.
3. Back up protected configs before modification.
4. Apply minimal reversible change.
5. Verify with actual command, test, log readback, or tool smoke.
6. Report changed files, verification and restart needed.

## Safety

- Do not edit other profiles unless user explicitly directs.
- Do not submit local `~/.hermes/hermes-agent` to GitHub without explicit authorization.
- Do not fabricate provider/model calls.
- For GPT/Claude custom providers configured as Responses API, do not use chat-completions.
- After `hermes update`, do not judge health by old/new file comparison or try to restore old overlays by default. Assess the current latest runtime for completeness and optimization: official repo integrity, config presence, active launchd/services, import/compile health, broken references, stale pycache-only directories, and root/workspace pollution. Missing historical overlays such as `apex_god/`, `se20/`, or PGG Archon `agent/pgg_archon_*`/`agent/apex_*` may be the intended optimized state. Treat stale launchd jobs, wrapper scripts pointing to absent modules, and pycache-only directories as cleanup candidates; restore old files only after explicit confirmation that the current optimized structure is incomplete.

## Reference

Full Hermes Agent usage notes archived at `references/full-skill-archive-20260601.md`.

For Desktop/Web UI bottom model selector issues where CLI/API works but UI switching fails, see `references/web-ui-custom-model-visibility.md`.
