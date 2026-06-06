# Audit score semantics and no-fake convergence repairs

Use this in PGG Archon truthful audits when health/status/convergence numbers appear to conflict.

## Core anti-fake rule

Never compare scores from different mouths as if they measure the same thing:

- runtime/background readiness score: service health, git state, watches/errors;
- external audit score: GPT/Claude/third-party reviewer score;
- self-eval capability score: Rust APEX ΔE item scores;
- convergence metric: loss/gap over time.

If a field is reused ambiguously, add metadata such as `score_type`, `benchmark_type`, and `note` rather than silently changing numbers.

## APEX ΔE direction rule

APEX ΔE is higher-is-better. If the convergence component expects lower-is-better, transform to a gap:

```python
convergence_gap = max_delta_e - delta_e
```

Store both raw `delta_e` and `convergence_gap` so the report is auditable.

## Path-root rule

When Rust `eval.rs` internally appends `evolution`, callers must pass `~/.hermes/workspace`, not `~/.hermes/workspace/evolution`. Double-joining can create fake low scores by looking under `workspace/evolution/evolution`.

## Reporting rule

A successful repair report must still list true gaps such as stale scout freshness, zero event-log activity, or untracked code. Do not create placeholder logs or stage broad untracked overlays to make a report look clean.
