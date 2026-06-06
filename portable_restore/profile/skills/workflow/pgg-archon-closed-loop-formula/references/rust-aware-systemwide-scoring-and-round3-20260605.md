# Rust-aware systemwide AGI scoring + Round3 closure (2026-06-05)

## Trigger

Use this reference when the user asks to audit PGG Archon / Apple Didi AGI progress, especially after 33-card ACTIVE, Rust-native evolution, or multi-LLM scoring.

## Key lesson

A valid AGI progress audit must include Rust-native runtime evidence. Do not score only from 33-card status cards, skills, manifest, or Python modules. Check the Rust modules and health watcher before final scoring.

## Required evidence to inspect

- Rust PyO3 modules:
  - `hermes_pgg_status`
  - `hermes_pgg_ecc`
  - `hermes_pgg_overlay`
  - `hermes_apex_evolution`
- Rust crate tests under `rust_modules/*`.
- Python import smoke for the compiled `.so` modules.
- launchd entry: `ai.hermes.evol-watcher`.
- Rust health snapshot:
  - `~/.hermes/data/pgg-background-evolution/rust_health_snapshot.json`
- Alpha/Psi truth gate:
  - `~/.hermes/data/pgg-background-evolution/alpha_psi_truth_gate.json`
- External triad run result:
  - `~/.hermes/workspace/audit/systemwide_agi_audit_20260605/triad_round2/triad_run_result.json`

## Correct scoring behavior

When Rust evidence is included, the score may increase relative to an evidence set that only sees status cards. In this session, Rust-aware scoring moved the estimate from `34/L1` to roughly `37–38/L1`, because Rust modules, tests, watcher, and health snapshot were real.

After Round3, Rust internal health reached:

```text
APEX ΔE: 5.0
pending_dimensions: []
alpha_psi_truth_gate: PASS 5/5
external triad: 100 benchmark specs + 50 safety specs + reproducible research smoke
```

However, this still does not prove L2 or full AGI. It is internal readiness evidence unless the benchmark/safety/research triad is actually run and scored.

## GPT participation rule

If the user asks to combine DeepSeek and MiniMax, and the active model is GPT/gpt5.5, Apple Didi must also participate as a third judge after checking live evidence. Do not only relay DeepSeek/MiniMax. The final evaluation should distinguish:

- external model structured scores,
- unstructured/parse-failed model outputs,
- Apple Didi / GPT independent assessment,
- engineering readiness vs real AGI capability.

## Top shortboards after Round3

1. The external triad is still a generated frozen spec/smoke; it must be run and scored.
2. MiniMax often returns visible output with `<think>` and malformed JSON; use a structured-output adapter before counting verdicts.
3. Rust ΔE 5.0 is internal health/readiness, not an external AGI benchmark.

## Boundary phrase

Use this boundary in reports:

```text
Rust ΔE 5.0 and 33/33 ACTIVE are internal engineering/readiness evidence; they do not prove L2 or full AGI without real external benchmark, safety, and research task execution.
```
