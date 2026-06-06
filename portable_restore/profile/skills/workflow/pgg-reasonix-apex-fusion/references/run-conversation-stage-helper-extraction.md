# run_conversation stage helper extraction pattern

## Scope
For Hermes core-loop evolution tasks around `agent/conversation_loop.py::run_conversation`, prefer a staged path:

1. Establish read-only RC characterization contracts（特征契约）and extraction readiness matrix（抽取就绪矩阵）.
2. Extract small mechanical helpers（机械辅助函数）inside RC-S01 first.
3. When the user asks for a larger step, promote from single-purpose helpers to stage helpers（阶段辅助函数）, but keep the boundary before provider/tool loop until stronger behavior-level tests exist.

## Safe larger-step examples
Durable examples from the 2026-06-02 session:

- `_bootstrap_turn_context(...)`: session/write-origin binding, primary runtime restore, input sanitization, stream/persist binding, task id binding, retry/runtime reset.
- `_prepare_turn_messages(...)`: compression warning replay, iteration budget, history copy, todo hydration, memory nudge hydration, scrubber resets, original user message, memory review trigger, user message append/persist index.
- `_prepare_system_prompt_and_preflight_compression(...)`: cached system prompt restore/build, preflight token estimate, compressor display sync, defer preflight, up to 3 compression passes, `conversation_history = None` after compression, retry/content flag reset.

## Testing requirement
For each stage helper, add behavior-level characterization tests（行为级特征保持测试）covering:

- return values that replace former locals;
- side-effect order when relevant;
- identity/copy semantics, especially `conversation_history` copy behavior;
- compression pass semantics, including repeated pass possibility;
- preservation of `conversation_history = None` after compression-created sessions;
- retry/content flags reset after compression.

## Slicer/window drift pitfall
Stage helper extraction moves AST signals out of fixed 500-line windows. A false WATCH can happen even when behavior is preserved.

Do NOT lower the contract gate. Instead, update the slicer（切片器）so contracts can verify either:

- the signal remains in the expected local RC window; or
- the signal exists in the all-function AST signal surface and is reachable through an extracted helper call.

Examples of signals that may drift after stage extraction:

- `_stream_callback`, `_persist_user_message_override`;
- `_pending_steer`, `response_invalid`, `update_token_counts`;
- `api_messages`, `_sanitize_messages_surrogates`;
- `agent._compress_context`, `agent._summarize_api_error`;
- output transform and turn explanation surfaces.

## Verification gate
Before claiming completion, run and record:

- RC-S01~RC-S09 contract status all PASS;
- extraction readiness matrix remains `RC_S01_MINIMAL_EXTRACTION_READY_WITH_GUARDRAILS` until RC-S02+ has stronger tests;
- targeted pytest for bootstrap helpers + slicer + CodeGenesis scanner;
- `py_compile` for edited Python files;
- `git diff --check`;
- `venv/bin/python -m apex_god.health`;
- `venv/bin/python -m apex_god.evolution_manifest --update`;
- scoped commit containing only the current round's files.

## Boundary
Do not extract RC-S02+ provider/tool loop merely because RC-S01 stage helpers pass. Entering RC-S02+ requires stronger behavior-level characterization and post-extraction regression first.
