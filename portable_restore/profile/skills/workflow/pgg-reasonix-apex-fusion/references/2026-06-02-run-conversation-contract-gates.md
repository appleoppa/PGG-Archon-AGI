# run_conversation read-only contract gates pattern

## Context

During PGG Archon / Hermes evolution work, `agent/conversation_loop.py::run_conversation` was identified as a central hotspot:

- ~4353 lines / 641 branches.
- CodeGenesis status remained `WATCH` due high duplication.
- Direct refactor was judged high risk.
- User requested autonomous continuation and real multi-LLM review.

## Durable technique

Before extracting or rewriting a large core loop, create read-only characterization contract gates:

1. Parse the target source with `ast`.
2. Do not import, execute, patch, or refactor the target function.
3. Split the function into deterministic source windows / slices.
4. For each slice, collect stable structural facts:
   - call names;
   - assignment targets;
   - name signals;
   - if/try/loop/call counts;
   - purpose / mutation boundary.
5. Convert critical invariants into `contract` booleans.
6. Emit `contract_status = PASS` only when all booleans pass.
7. Add tests that read the real source file and assert the contract remains stable.
8. Only after relevant windows have PASS gates should extraction readiness be considered.

## Multi-LLM routing pattern

For PGG Archon / AGI evolution tasks:

- GPT / Claude should be called through Responses API providers when configured.
- DeepSeek may be included as an additional channel when the user asks for all available LLM systems, but it should not replace GPT/Claude as the main evolution reviewer.
- MIMO can be used as third-party audit.
- Persist provider/model/status/path/hash evidence under the evolution evidence directory.

## Applied gates

The session added read-only contract gates for `run_conversation` windows:

- RC-S01: bootstrap/runtime/retry setup.
- RC-S02: message preparation / skill nudge / API kwargs / streaming setup.
- RC-S03: provider response status / invalid response / fallback / usage surface.
- RC-S04: API retry / interrupt / credential/image/unicode recovery / usage persistence.
- RC-S05: API error recovery / credential refresh / reasoning replay repair / context compression.

## Key pitfall

Do not treat these gates as a refactor. They are only a safety net. Keep reporting clear:

- `run_conversation` not modified.
- CodeGenesis may remain `WATCH` until duplication is actually reduced.
- Contract gates prove structure/invariants remain visible, not that behavior is exhaustively tested.

## Verification checklist

After adding or changing a contract gate:

1. Run targeted slicer tests plus relevant CodeGenesis tests.
2. Run `py_compile` on edited Python files.
3. Run `git diff --check`.
4. Run APEX-GOD health from the Hermes agent repo using the local venv.
5. Update `EVOLUTION_MANIFEST`.
6. Commit only the relevant code/test files.
7. Write a concise evidence report with model hashes and manifest hash.
