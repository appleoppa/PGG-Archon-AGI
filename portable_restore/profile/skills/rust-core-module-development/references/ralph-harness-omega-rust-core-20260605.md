# Ralph × Harness × Ω_A Rust Core Fusion — 2026-06-05

## Source

Desktop formula: `/Users/appleoppa/Desktop/Ralph 终极公式.md`.

Core absorbed ideas:

- Ralph loop: continue autonomous engineering iteration while objective verification fails.
- Harness: pre-action gates + post-action sensors; multi-layer verification beyond compile/test.
- Ω_A: external persistent memory/state, not prompt blob; maps to manifest + skill/reference + archive + retrieval store.
- ΔG: bounded evolution driving signal, interpreted as remaining gap/defect pressure.

## Mathematical correction

Original compact form:

```text
S_{t+1} = F(S_t, G) · I(¬V(S_t))
```

If `V(S_t)=True`, the expression multiplies by zero and loses the final state. The fused PGG form uses preserve-state semantics:

```text
S_{t+1}=I(¬V_H(S_t))*H[ΔG*F(S_t,G,Ω_A)] + I(V_H(S_t))*S_t
```

Passing verification marks the state as converged and preserves auditability.

## Claude review evidence

Real Claude call via `custom:claude_opus46_5yuantoken` / `claude-opus-4-6` / `codex_responses` returned a design review recommending:

- additive Rust crate only, pure computation;
- `RalphState`, `OmegaRef`, `HarnessPolicy`, `RalphOutput`;
- multi-layer Harness checks;
- explicit correction of state-zeroing issue;
- terminal states and tests for ΔG, invariants, property checks, no scheduler/security diff.

## Rust implementation

Crate:

```text
/Users/appleoppa/.hermes/hermes-agent/rust_modules/hermes_pgg_ralph
```

Python extension installed to Hermes venv:

```text
/Users/appleoppa/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hermes_pgg_ralph.abi3.so
```

Public Python functions:

- `version()`
- `sample_state_json()`
- `evaluate_state_json(state_json, policy_json=None)`

Schemas:

- `HermesPGGRalphCore/v1`
- `HermesPGGRalphHarness/v1`

## Verification evidence

- `cargo fmt`: PASS
- `cargo test`: 5 passed / 0 failed
- `cargo build --release`: PASS
- macOS codesign: PASS
- Python import smoke: PASS
- sample result:
  - `decision=converged`
  - `phase=converged_preserve_state`
  - `converged=True`
  - `corrected_formula=S_{t+1}=I(not V_H(S_t))*H[ΔG*F(S_t,G,Ω_A)] + I(V_H(S_t))*S_t`

## Boundary

This is a bounded additive Rust control surface. It does not make Hermes or PGG full AGI, does not run providers, and does not alter Hermes core scheduler/security boundary. It provides a deterministic, testable controller surface for future runtime integration.
