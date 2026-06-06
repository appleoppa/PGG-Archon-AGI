---
name: hermes-s6-container-supervision
description: Modify, debug, or extend the s6-overlay supervision tree inside the Hermes Agent Docker image — adding new services, debugging profile gateways, understanding the Architecture B main-program pattern.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [docker, s6, supervision, gateway, profiles]
    related_skills: [hermes-agent, hermes-agent-dev]
---

# Hermes s6 Container Supervision — Compact

## Trigger

Use when modifying, debugging, or extending s6-overlay supervision tree inside Hermes containers.

## Workflow

1. Identify service directory, run script, finish script, dependencies, and logs.
2. Verify container/process state before editing.
3. Make minimal service changes.
4. Restart/reload supervision in the least disruptive way.
5. Verify process health, logs, and port/socket readiness.

## Safety

Do not kill all services blindly. Preserve executable bits. Keep rollback copy of service files. Process existence is not readiness.

## Reference

Full command catalogue archived at `references/full-skill-archive-20260601.md`.
