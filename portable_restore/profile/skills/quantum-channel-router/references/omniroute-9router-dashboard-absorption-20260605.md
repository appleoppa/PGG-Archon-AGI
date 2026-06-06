# OmniRoute / 9router Dashboard Absorption Notes — 2026-06-05

## Trigger

Use these notes when absorbing an external LLM router/gateway project, implementing a Rust-native routing core, or adding dashboard/status surfaces for PGG Archon/Hermes routing.

## Key workflow lessons

1. If the active session model is already GPT and the user asks “use GPT to design,” do not call an external GPT endpoint by default. External GPT calls are only needed when the user asks for external/multi-model review.
2. For external router absorption, prefer structural learning over wholesale code ingestion: ingress compatibility, format translation, fallback policy, RTK/tool-result compression, provider cards, route evidence, and dashboard state.
3. Keep provider/OAuth/free-model bypass logic out of PGG core unless explicitly authorized and audited. Absorb patterns, not quota-bypass behavior.
4. A dashboard is not proof of upstream model participation. It should expose route decisions, provider scores, fallback/blocked reasons, RTK stats, and evidence boundaries.
5. For PGG, RTK/token saver must be evidence-preserving: legal citations, evidence IDs, file paths, diff hunks, and error lines must survive compression.
6. Rust route score should be property-tested. Clamp each score component and final score; property tests can catch overflow/weight mistakes.
7. Bridge Rust routing cores into Python status surfaces through bounded CLI/JSON outputs first; avoid immediately editing core scheduler/security boundaries.

## Minimal artifact pattern

- Rust crate: `rust_modules/<router_crate>/`
- CLI modes: `smoke`, `decide <text>`, `dashboard`
- Dashboard JSON schema should include:
  - `schema`
  - `summary.selected_provider/status/score`
  - `provider_cards[]` with health/quality/schema/cost/latency/compliance/supports
  - `decision.fallback_chain`
  - `decision.blocked`
  - `rtk.filter/bytes_before/bytes_after/preserved_anchors`
  - explicit `boundary`
- Python bridge should expose only status/data surface unless a real provider call is made.
- Tests:
  - Rust `cargo test` for route selection, cooldown blocking, RTK anchor preservation, score bounds.
  - Python pytest for bridge schema, dashboard presence, boundary wording, and file existence.

## Boundary wording

Use wording like:

```text
Dashboard/status surface only; not proof of upstream provider participation, no OAuth/free-provider bypass, not full AGI.
```

## Concrete signals from this session

- Existing `quantum-channel-router` skill needed an extra pitfall: active GPT session satisfies “use GPT” unless external review is explicit.
- 9router dashboard functionality worth absorbing: provider cards, fallback chain, blocked reasons, RTK token saver stats, route evidence ledger, and truth boundary.
- PGG/Hermes value-add over 9router: Rust-native core, evidence-preserving RTK, legal/AGI boundary gates, manifest readback, and quantum-router status integration.
