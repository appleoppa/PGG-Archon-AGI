# Context Compression Timeout & Hygiene Runbook (2026-06-02)

## When to use

Use when Hermes Gateway reports repeated context compression failures, hangs, premature `Session hygiene: auto-compressing`, `Compression summary failed`, auxiliary LLM timeout, or user reports recent context/compaction instability.

## Durable lesson

Do not assume token threshold is the only trigger. Gateway hygiene can trigger compression by **message count** before token count reaches `compression.absolute_threshold_tokens`.

## Diagnostic sequence

1. Check config values without printing secrets:
   - `compression.absolute_threshold_tokens`
   - `compression.threshold_safety_percent`
   - `compression.hygiene_hard_message_limit`
   - `auxiliary.compression.provider`
   - `auxiliary.compression.model`
   - `auxiliary.compression.timeout`
2. Inspect gateway logs for both trigger class and actual failure:
   - `Session hygiene: auto-compressing`
   - `threshold: absolute ... capped by ...`
   - `message count` / `messages`
   - `Failed to generate context summary`
   - `Compression summary failed`
   - `APITimeoutError`
3. Read the runtime code paths before changing values:
   - `agent/context_compressor.py` for summary input cap and serialization logic.
   - `gateway/run.py` for hygiene trigger logic.
   - `agent/auxiliary_client.py` for auxiliary LLM timeout/provider routing.
   - `agent/agent_init.py` for config loading.
4. Make a config backup before writing, because `config.yaml` contains provider/runtime state.

## Common root causes

- `compression.hygiene_hard_message_limit` too low: short-message sessions can hit the message-count hard limit and compress early even when token count is below threshold.
- `auxiliary.compression.timeout` too low: summary generation may exceed 60s during gateway load, provider queueing, or model latency.
- Auxiliary compression provider/model mismatch: verify with a live, small `call_llm` smoke test using the configured provider and model.
- Context input cap regression: verify `_SUMMARY_INPUT_MAX_CHARS` and that serialization truncates old content while preserving protected/tail turns.

## Minimum rollback fix pattern

Prefer config-only changes first when code already has sane truncation and tests pass:

- Increase `compression.hygiene_hard_message_limit` enough to avoid premature short-message compression while preserving a runaway-session guard. A previously verified value was `400`.
- Increase `auxiliary.compression.timeout` to tolerate provider/gateway load. A previously verified value was `180` seconds.
- Keep token thresholds unchanged unless logs prove token-based triggering is too early.
- Restart the Hermes gateway after config changes.

## Verification checklist

- Read back edited config values.
- Run a live auxiliary compression smoke call against `auxiliary.compression.provider/model`.
- Run context compressor and gateway hygiene tests when available.
- Verify no syntax errors in touched Python/YAML files.
- Restart gateway and confirm status/log connection.
- Update `EVOLUTION_MANIFEST.json` if this is part of PGG Archon/Hermes evolution work.

## Output shape

Report field-wise, not as a large table:

```text
status:
root_cause:
llm_audit:
fix_applied:
verification:
restart_needed:
next_watch:
```

## Pitfall

Do not report “fixed” from file existence or config write alone. For this class, fixed means: config readback + live auxiliary smoke + relevant tests + gateway restart/status.
