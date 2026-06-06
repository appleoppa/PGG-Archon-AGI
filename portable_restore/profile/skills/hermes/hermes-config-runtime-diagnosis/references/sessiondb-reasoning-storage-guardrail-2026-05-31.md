# SessionDB Reasoning Blob Storage Guardrail — 2026-05-31

## Problem pattern

A Hermes session can burn context even after compression/tool-output fixes because assistant messages persisted to SQLite may include verbose hidden fields:

- `reasoning`
- `reasoning_content`
- `reasoning_details`
- `codex_reasoning_items`
- `codex_message_items`

These blobs are useful inside the live turn for Responses/Codex-style provider replay, but they are usually low-value for long-term `session_search` and context recovery. In one audit, `codex_reasoning_items` alone contributed ~57K chars while user input was negligible.

## Durable fix pattern

Use a storage gate rather than deleting fields from live messages:

1. Keep full reasoning/codex state in the in-memory `messages` list.
2. Add a config-controlled gate for durable SessionDB writes, e.g.:

```yaml
session_storage:
  persist_reasoning: false
```

3. In the DB flush path, only pass hidden reasoning fields to `append_message(...)` when this option is true.
4. Default to false and fail closed on config read errors.
5. Preserve an opt-in path for debugging/provider audits.

## Implementation checklist

- Locate the session flush/persist path, commonly around `_flush_messages_to_session_db(...)` / `_persist_session(...)`.
- Add a small helper like `_session_db_reasoning_enabled()` that reads `hermes_cli.config.load_config()` and returns a boolean.
- Gate only the DB-write kwargs:

```python
reasoning=msg.get("reasoning") if role == "assistant" and persist_reasoning else None
codex_reasoning_items=msg.get("codex_reasoning_items") if role == "assistant" and persist_reasoning else None
```

- Do **not** mutate `msg` or `messages`; this avoids breaking provider-native replay.
- Add tests for both default-off and opt-in behavior.
- Verify with a live probe that DB kwargs are `None` while the source message still contains the reasoning fields.

## Regression tests to include

1. Default behavior drops all reasoning/codex blobs from `append_message` kwargs.
2. Source `messages[0]` still retains `reasoning` and `codex_reasoning_items` after persistence.
3. `session_storage.persist_reasoning: true` writes the blobs for opt-in debugging.
4. Existing strict-provider reasoning replay tests still pass.

## Verification commands

```bash
venv/bin/python -m pytest \
  tests/run_agent/test_run_agent.py::TestPersistUserMessageOverride \
  tests/run_agent/test_run_agent.py::TestReasoningReplayForStrictProviders \
  -q

venv/bin/python -m py_compile run_agent.py
git diff --check -- run_agent.py tests/run_agent/test_run_agent.py
```

## Pitfalls

- Do not describe this as disabling reasoning. It only changes durable storage; live provider replay must remain intact.
- Do not remove `codex_message_items` from in-memory assistant messages; some provider adapters may need them for continuity.
- Do not store huge hidden blobs by default just because `session_search` can technically index them; they usually degrade recall quality and token efficiency.
- Do not expose hidden reasoning content in reports or logs.
