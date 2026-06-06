# Tool Result Budget Token Guardrail — 2026-05-31

## Problem class

Hermes context can still grow explosively after compression is fixed if large tool outputs are retained directly in the transcript. In the observed failure chain, user text was tiny, but tool results and persisted tool/codex artifacts dominated the session size.

Typical high-risk tools:

- `session_search`
- `search_files`
- `terminal`
- `execute_code`
- `web_extract`
- `web_search`

## Durable repair pattern

Add a configurable `tool_result_budget` section instead of relying only on hardcoded defaults.

Known-good config shape:

```yaml
tool_result_budget:
  default_result_size_chars: 25000
  turn_budget_chars: 60000
  preview_size_chars: 800
  tool_overrides:
    terminal: 20000
    execute_code: 20000
    search_files: 16000
    session_search: 16000
    web_extract: 20000
    web_search: 16000
```

Implementation checklist:

1. Add/extend a budget config loader with safe coercion and fallback to historical defaults.
2. Sanitize tool override keys/values; ignore malformed or non-positive values.
3. Make single-result persistence use loaded config when the caller passes the default budget object.
4. Make per-turn budget enforcement use loaded config when the caller passes the default budget object.
5. Keep pinned/infinite thresholds, especially for `read_file`, to avoid persist-read-persist loops.
6. Preserve explicit `config=` arguments in tests and special call sites so callers can override runtime config deterministically.
7. Add tests for:
   - missing config falls back to defaults;
   - configured single-result threshold triggers persistence;
   - configured turn budget triggers persistence;
   - preview size is honored;
   - malformed overrides are ignored.

## Verification recipe

Run targeted tests and a small live probe:

```bash
venv/bin/python -m pytest tests/tools/test_tool_result_storage.py -q
venv/bin/python -m pytest tests/tools/test_tool_result_storage.py tests/tools/test_tool_output_limits.py tests/agent/test_context_compressor.py -q
git diff --check -- tools/budget_config.py tools/tool_result_storage.py tests/tools/test_tool_result_storage.py
venv/bin/python -m py_compile tools/budget_config.py tools/tool_result_storage.py
```

Live probe pattern:

```python
from unittest.mock import MagicMock
from tools.tool_result_storage import maybe_persist_tool_result, enforce_turn_budget, PERSISTED_OUTPUT_TAG

env = MagicMock()
env.execute.return_value = {"output": "", "returncode": 0}

r = maybe_persist_tool_result("x" * 30000, "terminal", "demo", env=env)
print(PERSISTED_OUTPUT_TAG in r, len(r))

msgs = [
    {"role": "tool", "tool_call_id": "a", "content": "a" * 35000},
    {"role": "tool", "tool_call_id": "b", "content": "b" * 35000},
]
enforce_turn_budget(msgs, env=env)
print(sum(PERSISTED_OUTPUT_TAG in m["content"] for m in msgs), [len(m["content"]) for m in msgs])
```

Expected shape: a large terminal/search result becomes a small persisted-output reference plus preview; multi-tool turn budget persists the largest result first.

## Deployment notes

- This guardrail complements compression; it does not replace hybrid compression thresholds.
- Restart the gateway after config/code changes and verify exactly one gateway process remains.
- Commit only the relevant budget/config/test files; do not mix unrelated PGG Archon formula or MCP files into token-governance commits.
