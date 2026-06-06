# run_conversation read-only contract gates and minimal extraction workflow

## Trigger
Use this reference when evolving or auditing `agent/conversation_loop.py::run_conversation` and the risk is too high for direct refactor.

## Durable workflow learned
1. Do **not** directly refactor the monolithic `run_conversation` loop first.
2. Build an AST-based slicer/characterization report around bounded line windows (RC-S01, RC-S02, ...).
3. For each window, extract read-only facts:
   - call targets
   - assigned state names
   - name signals
   - exception/branch density where useful
4. Convert stable facts into explicit contract fields with `contract_status = PASS/WATCH`.
5. Add real-source tests that assert the contract map is stable before allowing extraction.
6. Use multi-LLM review as an evidence gate when available, but do not substitute LLM agreement for tests.
7. Keep the mutation boundary explicit: `do not extract until RC-Sxx contract passes against real source`.
8. Run targeted pytest, py_compile, `git diff --check`, APEX-GOD health, and Evolution Manifest update before reporting completion.

## Extraction readiness matrix gate
Before mutating `run_conversation`, add a separate read-only extraction readiness matrix. The matrix should:
- verify all RC-S01...RC-S09 contracts are `PASS` against real source;
- carry an explicit schema/version such as `PGGArchonRunConversationExtractionReadinessMatrix/v1`;
- include a numerical readiness score and a conservative status;
- allow only one narrowly scoped extraction, e.g. `allow_minimal_rc_s01_extraction = true`;
- explicitly forbid RC-S02+ extraction, bulk rewrite, provider/tool behavior changes, scheduler mutation, and security-boundary mutation;
- be tested from real source and, when useful, persisted as JSON under the evolution evidence directory.

Recommended decision rule: even if the score is high enough to allow RC-S01 minimal extraction, do **not** combine matrix creation and production code extraction in the same step. First commit the matrix, then perform one minimal extraction in a later step.

## Minimal extraction pattern after matrix approval
When the matrix allows RC-S01 minimal extraction:
1. Re-read the exact source slice and identify the smallest mechanical helper candidate.
2. Prefer pure state setup/reset helpers over provider/tool/persistence paths.
3. Move the exact assignments into a private helper near `run_conversation`, e.g. `_reset_turn_runtime_state(agent)`.
4. Replace the original in-function block with one helper call.
5. Add a characterization test for the helper that initializes non-default values and asserts the exact reset contract.
6. Run the full targeted gate again: helper test, slicer tests, CodeGenesis-related tests, py_compile, `git diff --check`, APEX-GOD health, Manifest update.
7. Report explicitly whether `agent/conversation_loop.py` was modified and whether `run_conversation` has actually been refactored.

Good first extraction example: reset retry counters, post-tool flags, guardrail state, Unicode sanitization pass count, and vision support into `_reset_turn_runtime_state(agent)`. This is low-risk because it has no provider call, no persistence, no tool execution, no scheduler/security boundary behavior, and can be characterized with a simple fake agent object.

## Evidence discipline
- Save provider responses and hashes under `~/.hermes/workspace/进化/证据/...`.
- Redact all credentials and never copy API keys/tokens into reports.
- Report which providers returned HTTP 200 and which failed/time out.
- If tool output is truncated, persist summaries to files and read back only key fields.
- Avoid overclaiming: state whether CodeGenesis remains WATCH when high duplication is still present.
- When using shell wrappers such as `rtk`, inspect the returned summary carefully; if the diff preview omits newly added tests, verify that `git add`/commit actually included them before claiming they were committed.

## Boundary
This workflow distinguishes three states:
- characterization gates exist;
- extraction readiness matrix allows a bounded extraction;
- `run_conversation` was actually modified by a minimal helper extraction.

Do **not** conflate them. The workflow does **not** mean:
- the whole `run_conversation` has been refactored,
- RC-S02+ extraction is allowed,
- CodeGenesis has passed if duplication remains high,
- Hermes core scheduler or security boundary has changed.
