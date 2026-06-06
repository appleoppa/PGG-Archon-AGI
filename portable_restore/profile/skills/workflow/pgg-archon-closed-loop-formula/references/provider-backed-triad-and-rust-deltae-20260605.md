# Provider-backed triad vs spec/scorer validation + Rust ΔE health — 2026-06-05

## Durable lesson

A frozen triad can validate the evaluation *specification* without proving model capability. Treat these as separate states:

```text
SPEC_READY        = benchmark/safety/research items exist and are hashable
SCORER_VALIDATED  = deterministic completeness scorer passes
PROVIDER_RUN      = real model/system responses generated and raw outputs saved
CAPABILITY_SCORE  = provider outputs scored against the frozen scorer
LLM_REVIEWED      = multiple LLM judges review the scored report with boundaries
```

Do not collapse `SCORER_VALIDATED` into `CAPABILITY_SCORE`.

## Pattern that worked

1. Build frozen benchmark/safety/research specs.
2. Add deterministic evaluator to validate spec completeness.
3. Run tests on adapter + triad + evaluator.
4. Call multiple LLMs to review the result.
5. Preserve strict boundary wording in manifest: deterministic scorer PASS is not a real provider benchmark.

## MiniMax structured-output adapter

MiniMax-M3 often returns visible output as:

```text
<think>...</think>
{...json...}
```

Reusable parser steps:

1. Strip `<think>...</think>`.
2. Try direct `json.loads`.
3. Extract first `{...}` window.
4. Use balanced-brace fallback.
5. If still failing, keep `json_parse_failed`; never count as PASS.

## Rust ΔE health lesson

Rust health can legitimately show internal readiness progress, but it is not an external AGI score. Keep the distinction:

```text
Rust ΔE 5.0 = internal health/readiness
AGI score   = external/general capability evidence
```

If `pending_dimensions=[]` but low-level items still show incomplete counts, future audit must explain the mapping rather than treating the number as AGI capability.

## Next-step gate

Before claiming L2 movement, require at least one provider-backed run:

- raw provider responses saved
- scorer hash saved
- pass/fail rates computed
- failure cases included
- 5-LLM review with `WATCH/PASS/ERROR` preserved per provider
