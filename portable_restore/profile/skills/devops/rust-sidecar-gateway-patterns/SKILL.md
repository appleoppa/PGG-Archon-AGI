---
name: rust-sidecar-gateway-patterns
description: Rust sidecar gateway 的可吸收架构模式：多 provider、飞书/聊天上下文、错误分诊、持久化账本、部署清理
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rust, sidecar, gateway, feishu, llm, deployment, cleanup]
---

# Rust Sidecar Gateway Patterns — Compact

## Trigger

Use for Rust sidecar gateways, multi-provider routing, Feishu/chat context handling, persistent ledger, error triage and deployment cleanup patterns.

## Absorbable patterns

- Provider abstraction with explicit API modes.
- Context envelope carrying platform/profile/thread safely.
- Durable request/response ledger for audit.
- Health check and structured error taxonomy.
- Clean start/stop and no duplicate gateway ownership.

## Boundary

NanoGPT-claw/NanoGPT-AGI local deployment is retired; only generalized patterns are retained. Do not restore its services/secrets/skills.

## Reference

Full sidecar notes archived at `references/full-skill-archive-20260601.md`.
