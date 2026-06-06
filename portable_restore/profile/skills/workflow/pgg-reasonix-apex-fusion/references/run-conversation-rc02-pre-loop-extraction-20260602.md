# run_conversation RC-S02 pre-loop extraction pattern — 2026-06-02

## Trigger
Use this reference when continuing PGG Archon / Hermes `run_conversation` governance after RC-S01 helpers are already extracted and the next step is feasible (>75%), low risk, and reversible.

## User workflow correction
The user explicitly corrected the execution style: when the next step is >75% feasible and low-risk/reversible, continue directly. Do not pause to ask whether to proceed; perform the next bounded implementation, run gates, write evidence, commit scoped files, and report proof.

## Safe RC-S02 first-slice pattern
Before touching provider call or tool execution, extract only pre-loop/pre-provider logic:

1. `pre_llm_call` plugin context collection into a helper such as `_collect_pre_llm_plugin_context(...)`.
   - Keep context ephemeral and inject into the user message later, not into the system prompt.
   - Preserve dict `context` and non-empty string handling.
   - Preserve non-fatal hook exception behavior.

2. memory manager turn-start + external memory prefetch into a helper such as `_prepare_pre_loop_memory_context(...)`.
   - Call `on_turn_start(turn_count, message)` before `prefetch_all(query)`.
   - Use original clean user message; for non-string input use `""`.
   - Keep provider exceptions non-fatal and return `""` on failure.
   - Do not call provider/model/tool paths inside the helper.

## Characterization tests to add
Add behavior-level tests for each helper before claiming completion:

- plugin hook returns mixed dict/string context and joins with blank lines;
- plugin hook exception returns empty context;
- memory manager receives `on_turn_start` then `prefetch_all` for string input;
- non-string input uses empty string for both turn message/query;
- memory provider exceptions do not block the turn and return empty prefetch context.

## Contract gate drift pitfall
After larger helper extraction, fixed RC window boundaries can drift while the real AST signals remain in `run_conversation` or helper/full-function scope. Do not weaken gates to pass blindly. Instead, for moved signals, update the contract to accept `window OR all_calls/all_assigns/all_names` when the original semantic signal still exists. Examples from this session:

- RC-S02 `retry_count/max_retries` may move outside the old window;
- RC-S05 `agent.clear_interrupt` may drift;
- RC-S08 status/fallback signals may drift;
- RC-S09 pending steer drain may drift.

Always rerun RC-S01~RC-S09 contract gates after slicer changes.

## Required validation before commit
Run and record:

- RC-S01~RC-S09 contract gate: all PASS;
- extraction readiness matrix status;
- targeted pytest for helper tests and slicer tests;
- `py_compile` for edited Python files;
- `git diff --check`;
- `python -m apex_god.health`;
- `python -m apex_god.evolution_manifest --update` and SHA256 readback;
- scoped evidence report under `~/.hermes/workspace/进化/证据/`;
- scoped commit with only this round's files staged.

## Boundaries
Do not claim CodeGenesis PASS if health reports WATCH. Do not modify Hermes core scheduler or security boundary. Do not extract provider call or tool execution under this pre-loop pattern.
