# run_conversation read-only contract gates pattern — 2026-06-02

## When to use
Use this pattern when a core runtime function is too large/high-risk to refactor directly, especially `agent/conversation_loop.py::run_conversation` or similar orchestrator loops.

## Trigger signals
- Large hotspot found by CodeGenesis/AST scanner.
- User asks to “继续” / “自行评估方向，继续”.
- Refactor would touch core scheduler, security boundary, provider call path, tool execution, persistence, or context compression.
- Code quality status is WATCH but parse/test/health are otherwise stable.

## Core rule
Do not jump from hotspot diagnosis to extraction. First build read-only characterization contract gates:

1. Parse source with `ast` only.
2. Do not import or execute the target function.
3. Split the function into stable line windows/slices.
4. For each slice, collect:
   - call signals
   - assign/state signals
   - name signals
   - risk/purpose/mutation boundary
5. Convert each slice into a `contract` dict and `contract_status`.
6. Add tests that read the real source file and assert the contract is PASS.
7. Only after all relevant slices pass should extraction readiness be evaluated.

## Proven slice sequence for run_conversation
- RC-S01: turn bootstrap / runtime context / retry counters.
- RC-S02: message preparation / skill nudge / API kwargs / retry and streaming setup.
- RC-S03: provider response status / invalid response / fallback / usage / assistant message surface.
- RC-S04: API retry / interrupt / cost and usage persistence / credential-image-unicode recovery.
- RC-S05: API error recovery / credential refresh / reasoning replay repair / context compression.
- RC-S06: context length failure / compression exhaustion / billing-entitlement guidance / final error surface.
- RC-S07: assistant response normalization / interim assistant message / tool call validation / tool execution entry.
- RC-S08/RC-S09: final response rendering / memory side effects / turn cleanup / persistence / hooks.

## Multi-LLM use
For AGI/PGG Archon evolution work, call all available configured model systems that are appropriate for the task and record:

- provider
- model
- API mode
- HTTP status
- evidence path
- SHA-256
- concise extracted verdict

Do not let model calls replace local tests. Model opinions only choose/confirm the direction; local AST contracts and tests are the deliverable.

## Verification close
Before reporting completion:

- targeted pytest for slicer and scanner tests
- `py_compile` for edited Python files
- `git diff --check`
- `python -m apex_god.health` from the Hermes agent venv/workdir
- `python -m apex_god.evolution_manifest --update`
- scoped commit with only current files staged
- concise evidence report under `workspace/进化/证据/`

## Pitfalls
- Do not claim duplication is fixed if CodeGenesis still reports WATCH.
- Do not claim `run_conversation` was refactored when only the slicer/contracts changed.
- Do not modify `agent/conversation_loop.py` while the task boundary is read-only contract gates.
- Do not stop after LLM review; implement the selected low-risk gate and verify it.
- Do not overfit contracts to line numbers alone; include semantic call/assign signals so tests fail on meaningful drift.
