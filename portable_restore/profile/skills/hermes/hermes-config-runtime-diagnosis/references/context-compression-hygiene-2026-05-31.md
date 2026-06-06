# Context Compression Hygiene: Token Explosion Guardrail

## Problem Pattern

A long Hermes/gateway task can burn provider daily quota when all of these happen together:

1. Tool outputs from long tasks accumulate in session history.
2. Compression triggers too late.
3. The compressor builds a summary prompt from old tool results without a global serialized-input cap.
4. The summary request itself becomes huge (for example, ~150k token scale), then the primary GPT/Claude daily quota is spent on compression rather than user work.

## Durable Fix Shape

Use layered controls; do not rely on only one threshold:

- Separate **when to compress** from **what to send to the summarizer**. The trigger threshold should prevent runaway sessions; the summarizer input cap should prevent the compression call itself from becoming a quota bomb.
- Prefer hybrid trigger config over a pure percentage across mixed-context models: `absolute_threshold_tokens: 150000` capped by `threshold_safety_percent: 0.70`, with `compression.threshold` retained as fallback/legacy behavior.
- Use a lightweight compression provider/model where possible.
- Put a hard character cap on the serialized messages sent to the summarizer; one known-good value is `80_000` chars.
- Build summarizer input newest-first (`reversed(turns)`) so recent context survives when the cap is reached.
- Keep an omission note such as `older compacted turn(s) were omitted` so future agents know history was intentionally truncated.
- Redact secrets before summary serialization; API keys, tokens, passwords, and bearer strings must not be preserved into compacted summaries.
- Verify gateway pre-agent hygiene also honors the same hybrid trigger config; avoid separate hardcoded thresholds like `0.85` in gateway code.

See `hybrid-compression-threshold-2026-05-31.md` for implementation details.

## Verification Recipe

Run targeted tests for both compressor and gateway hygiene:

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -m pytest tests/agent/test_context_compressor.py tests/gateway/test_session_hygiene.py -q
```

Probe live gateway logs after restart:

```bash
tail -n 100 ~/.hermes/logs/gateway.log | egrep -i 'Session hygiene|compressed|threshold'
```

Expected healthy log shape:

```text
Session hygiene: ... auto-compressing (threshold: 15% of 256,000 = 38,400 tokens)
Session hygiene: compressed ... → ... msgs, ... → ... tokens
```

Check for duplicate gateway processes before declaring runtime fixed:

```bash
ps aux | egrep 'hermes_cli.main gateway run|gateway run --replace' | grep -v egrep
hermes gateway status
```

Expected shape: one default gateway process, loaded service, and the updated source code has been restarted/loaded.

## Pitfalls

- Passing compressor unit tests is not enough if gateway hygiene has its own trigger threshold.
- Restart helpers may time out while still successfully replacing the gateway; verify by process count and logs rather than only command exit text.
- Manual background gateway starts can temporarily create duplicate gateway processes; after launchd is restored, kill the manual process and confirm only one remains.
- Do not mix unrelated worktree changes into the compression fix commit; commit only the compressor/gateway hygiene files for this class of repair.
