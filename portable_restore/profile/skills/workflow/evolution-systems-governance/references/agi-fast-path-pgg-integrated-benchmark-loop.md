# AGI Fast Path: PGG Integrated Benchmark Loop Pattern

Session date: 2026-06-03

## Why this pattern exists

The user corrected the trajectory: AGI evolution must be based on the already-built PGG Archon/APEX/Rust/self-evolution core, not isolated demo modules. The fastest credible route is task-failure-driven evolution connected to the system's real governance surfaces.

## Class-level pattern

Use this when asked to push PGG Archon/AGI evolution quickly with broad authorization.

### Sprint 1 — Minimal deterministic benchmark loop

Implement or reuse:

```text
task → prediction → deterministic scoring → failed examples → evolution queue
```

Required outputs:

- run JSON
- per-task scores JSONL
- failed-task evolution_queue JSONL
- tests proving PASS and WATCH paths

Boundary wording:

- internal benchmark harness only
- not full AGI
- not external benchmark
- not legal correctness proof

### Sprint 2 — Integrate with existing PGG core

Do not leave Sprint 1 as an isolated harness. Connect it to existing verified surfaces:

- Delta-G / anti-hallucination gate (`agent.pgg_archon_delta_gate`)
- Rust read-only status surface (`hermes_pgg_status`)
- Rust ECC surface (`hermes_pgg_ecc`)
- APEX ΔE evaluator (`hermes_apex_evolution`)
- fusion ledger and `EVOLUTION_MANIFEST.json`

The integrated result should include benchmark_run, pgg_status, pgg_ecc, delta_gate, apex_delta_e, output paths, queue count, and boundary statement.

### Sprint 3 — Provider-backed benchmark

Upgrade from sample predictions to configured real providers:

- GPT/Claude through Responses API (`/v1/responses`, not chat completions)
- DeepSeek through chat completions
- capture prediction per task
- score each provider through the integrated PGG loop
- rank providers by deterministic score and queue failures

Use dependency injection (`provider_call`) in tests so fake providers can prove logic without external calls. Real provider smoke tests should be small and explicitly labelled internal.

## Continuous authorization discipline

If the user authorizes continuous evolution, after each completed stage ask internally:

- Is next-step necessity >75%?
- Is it low-risk and reversible?
- Can it be verified by tests/readback/commit/ledger?

If yes, continue directly. Do not stop after a plan.

## Tool-call style for this user

Before each tool call, give a short Chinese estimate of runtime, e.g.:

```text
我现在运行核心测试并读回账本；预计 20–40 秒完成。
```

## Evidence gate

Every sprint should end with:

1. tests or real smoke run
2. model audit when architecture claims are involved
3. git commit of only relevant files
4. completion evidence JSON with SHA256
5. fusion ledger update and readback
6. `EVOLUTION_MANIFEST.json` update and readback

## Pitfalls

- Do not present a standalone harness as AGI evolution; connect it to existing PGG/Rust/APEX core.
- Do not claim provider participation unless real API calls were made and outputs were read back.
- Do not batch-submit ignored overlays or high-side-effect runtime files.
- Do not confuse internal task baselines with external AGI benchmarks.
