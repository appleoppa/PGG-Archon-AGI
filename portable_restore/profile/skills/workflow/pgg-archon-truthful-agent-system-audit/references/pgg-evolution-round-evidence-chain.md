# Round-style PGG/Hermes evolution evidence chain

Use for multi-round PGG/Hermes evolution work that combines local runtime repairs, model audits, GitHub/open-source references, Rust ΔE evaluation, overlay governance, and manifest updates.

## Durable workflow

1. Establish a factual baseline before model calls.
   - Git status/commit.
   - Active services/processes if relevant.
   - Import smoke for claimed modules.
   - Targeted pytest.
   - Current evaluator output and score semantics.

2. Keep score mouths separate.
   - Ledger/workspace score: may depend on accumulated evidence, scout files, event logs.
   - Fresh/root score: measures what the evaluator can see from the supplied path.
   - Runtime health score: infrastructure readiness.
   - External audit/benchmark: only if actually run.

3. If an evaluator path misses existing evidence, index real artifacts instead of fabricating evidence.
   - Build pointer/index files from existing reports, hashes, source scout summaries and event logs.
   - Mark them as derived from existing artifacts.
   - Re-run the evaluator and report before/after.

4. For model audits, call providers with evidence packs, not claims.
   - Record provider, model, endpoint, HTTP status, usage, output path.
   - If a provider fails, capture the exact API failure and retry only with a justified parameter adjustment.
   - Do not use the current main chat model as a substitute for an independent audit call unless explicitly stated.

5. Overlay governance.
   - For ignored/historical overlays, first produce inventory: path, importability, symbols, references, hash, classification.
   - Do not bulk commit or bulk delete ignored overlays.
   - Promote/archive/delete decisions must be per module.

6. Complete with readback.
   - Write a round evidence JSON under the workspace artifacts directory.
   - Update the domain ledger and `EVOLUTION_MANIFEST.json`.
   - Read back the updated lines before final response.
   - Commit only reproducible source code for the current theme; do not mix reports/ledgers unless intended.

## Provider quirks learned

- A Responses-style GPT proxy may return SSE text or complain about unsupported `max_tokens`; retry with `max_completion_tokens` only and parse JSON only if the response is JSON.
- A HTTP 200 response is not proof of visible model output. Extract and verify `output[].content[].text` or equivalent.

## Status wording

Use `PASS_WITH_BOUNDARY` when the engineering target is verified but the result is bounded.
Use `WATCH_GOVERNED` when the risk is inventoried and controlled but not eliminated.

Never turn internal readiness scores into full AGI, 10x, legal correctness, or external benchmark claims.
