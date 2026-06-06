# Claude-coded health repair pattern — 2026-06-03

## Context

A desktop audit report identified PGG Archon health/runtime gaps. User required that coding fixes be authored by Claude, while all LLM participation had to be real provider calls, not roleplay.

## Durable pattern

1. **Extract exact runtime interfaces before asking Claude to code.**
   - Read the failing health/check code and collect the exact import names, call signatures, expected return keys, and health predicates.
   - Do not rely on a natural-language audit summary or the first model patch if it has not seen exact interfaces.

2. **Call Claude through Responses API for coding fixes and record evidence.**
   - Use the configured Claude custom provider with `/responses` / `codex_responses` discipline.
   - Save provider/model/http status/elapsed/output path.
   - If Claude emits tool-use XML or asks for filesystem access instead of code, re-call with explicit constraints: plain text only, no `<tool_use>`, no external filesystem request, `tool_choice: none` when supported.

3. **Apply only interface-compatible code.**
   - First Claude pass may describe useful shapes but still mismatch health.py (e.g. tuple returns while health expects dict keys).
   - Re-prompt Claude with exact expectations, then adapt only as needed to preserve existing tests and schema compatibility.

4. **Preserve legacy behavior while adding compatibility.**
   - For compatibility wrappers, save the legacy function first (e.g. `_legacy_calc_delta_g = calc_delta_g`) and dispatch new input types separately.
   - Verify old tests still pass, not just the new health check.

5. **Verification sequence.**
   - `py_compile` target files.
   - Module smoke for each new import/function and a legacy-path smoke if a wrapper was added.
   - Focused regression tests (e.g. anti-hallucination E2E).
   - Full health check.
   - Run convergence cycle/status and report remaining truthful gaps.

## Pitfalls

- Health 24/24 is not the same as system capability convergence. If convergence_bridge still reports self/external deviation, keep it as an active warning and do not claim total repair.
- GitHub/open-source search may hit rate limits. Capture the actual rate-limit boundary and absorb only general patterns unless upstream code has been fetched, reviewed, and tested.
- Do not commit or stage broad untracked overlays automatically; report the untracked status and ask/continue only if version-control scope is authorized.

## Evidence shape for final report

Include:
- input audit report path + sha256;
- real LLM call metadata for GPT/Claude/DeepSeek/MIMO;
- explicit statement that coding was Claude-authored;
- changed files;
- py_compile / smoke / tests / health / convergence outputs;
- remaining gaps that are not fixed.
