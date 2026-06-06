# 9router → PGG OmniRoute fusion notes (2026-06-05)

## Trigger

Use when absorbing an external LLM gateway/router pattern (e.g. 9router) into PGG/Hermes quantum routing, especially when the user asks to compare it with 河图洛书 / 量子路由 or implement a Rust-native router core.

## User correction captured

If the active conversation model is already GPT and the user says "用 GPT 设计", treat that as "use the current GPT session to design". Do **not** spend an extra external GPT provider call unless the user explicitly asks for external GPT, multi-model review, or independent provider audit.

## Architecture distinction

- **9router**: local AI gateway/provider router. Main value: `/v1` compatibility, provider fallback, format translation, RTK token saving, usage/dashboard.
- **Quantum Channel Router**: task/model/channel routing with route evidence. Main value: deciding which model/provider should handle a task and recording truthful participation evidence.
- **河图洛书 / EVM**: cognition/evolution/order layer. Main value: sequence logic, defect governance, and evolution constraints; it is not a provider gateway.
- **PGG OmniRoute**: fusion target: Rust-native executable core combining safe 9router patterns + quantum routing + PGG/EVM gates.

## Safe absorption pattern

Absorb structure, not risky account behavior:

1. Universal ingress idea (`/v1`, Responses, Claude/Gemini/Codex adapters).
2. Provider score routing: task-fit, health, quality, schema reliability, cost, latency, compliance, recent failure debt.
3. Fallback chain with cooldown/model lock.
4. Evidence-preserving RTK: compress tool output but preserve legal citations, evidence IDs, file paths, diff hunks, error lines.
5. Route evidence ledger: selected provider, model, status, score, visible output chars, fallback reason, boundary.
6. Explicit boundary: a route decision is **not** proof that a provider participated; provider participation requires upstream call evidence.

## Rust implementation lessons

For Rust-native router cores:

- Keep first implementation additive: independent crate + CLI smoke + tests before wiring into Hermes core.
- Use property tests for route score bounds; weighted scoring can exceed 1.0 if positive weights sum above 1, so clamp the final score to `[0,1]`.
- Include tests for gates: Responses-required blocks chat-only providers; cooldown blocks unavailable providers; evidence-preserving RTK keeps legal/error anchors.
- Avoid copying JS/Next/OAuth/free-provider behavior from external routers into Hermes core. Implement provider adapters only behind explicit policy and evidence gates.

## Suggested fusion layers

```text
L1 Gateway compatibility: /v1, Responses, Claude, Gemini, Codex
L2 Provider state: health, fallback, cooldown, model lock, cost, latency
L3 Quantum routing: task class, route score, model strategy, route evidence
L4 河图洛书/EVM: sequence logic, defect/order factors, evolution priority
L5 PGG gates: legal truth, AGI boundary, manifest readback, provider participation proof
```

## Verification minimum

- `cargo test` passes.
- Smoke emits route decision JSON and RTK stats.
- Ledger entry includes truthful boundary.
- Manifest/readback only after the crate and smoke evidence exist.
