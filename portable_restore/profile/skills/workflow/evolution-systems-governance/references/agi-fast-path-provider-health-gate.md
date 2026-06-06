# AGI Fast Path — Provider Benchmark + Health Gate Pattern

Session pattern captured from PGG Archon Sprint3–Sprint4.

## Trigger

Use when the user authorizes rapid AGI/PGG evolution and the system already has an internal benchmark or integrated PGG benchmark loop.

## Core lesson

Do not stop at `task -> scoring -> evolution_queue`. The next high-ROI step is:

`real provider predictions -> PGG integrated scoring -> provider ranking -> provider health gate -> routing recommendation -> failure/evolution queue`

This keeps AGI evolution grounded in existing PGG Archon/Rust/APEX infrastructure instead of isolated demo harnesses.

## Durable workflow

1. Run the same deterministic benchmark tasks through configured providers.
   - GPT/Claude via Responses API.
   - DeepSeek/MIMO via chat completions when configured that way.
2. Preserve raw provider-call audit evidence.
   - HTTP status.
   - usage.
   - response preview.
   - attempts.
   - empty output / transport error reason.
3. Score predictions through the existing benchmark harness.
4. Route each provider result through the PGG integrated loop.
   - Rust `hermes_pgg_status`.
   - Rust `hermes_pgg_ecc`.
   - Delta-G / anti-hallucination signal.
   - `hermes_apex_evolution` APEX ΔE.
   - evolution queue.
5. Build a provider health gate.
   - Separate transport failure from model capability failure.
   - Do not treat API gateway failure as model incompetence.
   - Emit routing recommendations.
6. Commit only tracked code/tests for the current sprint.
7. Update fusion ledger + EVOLUTION_MANIFEST and read both back.

## Health classification pattern

- `HEALTHY / PRIMARY_CANDIDATE`: high score and no transport failures.
- `DEGRADED_CAPABILITY / FALLBACK_OR_SPECIALIZED`: model responds, but benchmark score is partial.
- `UNSTABLE_TRANSPORT / FALLBACK_UNTIL_RECOVERED`: mixed transport failures.
- `DOWN / BLOCK_PROVIDER_USE_FALLBACK`: all or dominant failures are provider/API/transport failures.
- `LOW_SCORE / DO_NOT_ROUTE_UNTIL_IMPROVED`: responses are available, but task score is low.

## Scorer robustness pattern

Provider output may be harmlessly wrapped despite a strict prompt. For deterministic JSON scoring, accept:

- raw JSON object text;
- fenced JSON blocks like ```json ... ```;
- short prefix/suffix text containing one JSON object.

Still require parsed JSON equality. Do not accept semantically vague text as JSON success.

## Pitfall from session

If the user has granted continuous evolution authorization, do not finish a turn with “next step should be ...” when the next step is necessary >75%, low-risk, and reversible. Execute it immediately. A report that merely says what should happen next is a process failure in this task class.

Also keep the todo list synchronized before context compaction; stale in-progress items can hide completed work and trigger user frustration.

## Boundary language

Always label this as internal provider benchmark / routing guidance. It is not:

- full AGI;
- external AGI benchmark success;
- legal correctness proof;
- proof that a provider is globally superior.

The health gate is a local routing signal based on the current benchmark and current provider transport state.
