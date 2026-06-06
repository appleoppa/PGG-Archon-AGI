# Hybrid Compression Threshold: Absolute Trigger + Model Safety Cap

## Session Lesson

A pure percentage compression trigger is not portable across mixed-context models:

- `0.15 × 1,000,000 ≈ 150,000` tokens: reasonable for a GPT-5.5-class large-context model.
- `0.15 × 256,000 = 38,400` tokens: too early for a MiniMax 256K model; gateway may compress after only a moderate tool-heavy exchange.

The stable repair is a hybrid threshold:

```python
threshold_tokens = max(
    min(absolute_threshold_tokens, int(context_length * threshold_safety_percent)),
    MINIMUM_CONTEXT_LENGTH,
)
```

Recommended default shape for this user's Hermes runtime:

```yaml
compression:
  enabled: true
  threshold: 0.15                 # legacy/fallback percent
  absolute_threshold_tokens: 150000
  threshold_safety_percent: 0.70
```

Expected derived thresholds:

```text
context_length=1,000,000 -> threshold=150,000
context_length=256,000   -> threshold=150,000
context_length=128,000   -> threshold=89,600
```

## Implementation Checklist

Patch both runtime paths; doing only the agent compressor leaves gateway pre-agent hygiene drifting.

1. `agent/context_compressor.py`
   - Add `absolute_threshold_tokens` and `threshold_safety_percent` constructor args.
   - Clamp safety percent, e.g. `0.10 <= safety <= 0.95`.
   - Derive `threshold_tokens` through a helper such as `_derive_threshold_tokens(context_length)`.
   - Preserve percent behavior when no valid absolute threshold is configured.
   - Keep `MINIMUM_CONTEXT_LENGTH` as the floor.

2. `agent/agent_init.py`
   - Read `compression.absolute_threshold_tokens` as positive int or `None`.
   - Read `compression.threshold_safety_percent` as float with fallback.
   - Pass both into `ContextCompressor(...)`.

3. `gateway/run.py`
   - Read the same config keys for session hygiene.
   - Use the same formula for `_compress_token_threshold`.
   - Log a human-readable threshold description, e.g. `absolute 150,000 capped by 70% of 256,000 = 150,000 tokens`.

4. `~/.hermes/config.yaml`
   - Add `absolute_threshold_tokens: 150000` and `threshold_safety_percent: 0.70` only after code supports them.
   - Preserve `threshold` as fallback/legacy config.

## Tests to Add

Agent compressor tests:

- large context 1,000,000 + absolute 150,000 + safety 0.70 -> 150,000
- 256,000 context + absolute 150,000 + safety 0.70 -> 150,000
- 128,000 context + absolute 150,000 + safety 0.70 -> 89,600
- no absolute threshold -> legacy percentage behavior remains

Gateway hygiene tests:

- With 256K context, `threshold: 0.15`, `absolute_threshold_tokens: 150000`, and `threshold_safety_percent: 0.70`, a ~50K-token session should **not** compress solely because 15% would be 38.4K.
- A session exceeding 150K tokens should compress.

## Verification Commands

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -m pytest tests/agent/test_context_compressor.py tests/gateway/test_session_hygiene.py -q
venv/bin/python -m py_compile agent/context_compressor.py agent/agent_init.py gateway/run.py
git diff --check -- agent/context_compressor.py agent/agent_init.py gateway/run.py tests/agent/test_context_compressor.py tests/gateway/test_session_hygiene.py
```

After config update and gateway restart:

```bash
hermes gateway restart
hermes gateway status
pgrep -fl 'hermes_cli.main gateway run|gateway run --replace' | grep -v grep || true
tail -n 100 ~/.hermes/logs/gateway.log | egrep 'Gateway|connected|Session hygiene|threshold'
```

Expected runtime shape:

- Gateway process count exactly 1.
- Gateway connected to intended platforms.
- Logs show hybrid/absolute threshold description on the next hygiene event.

## Commit Discipline

When other PGG Archon or MCP files are dirty, stage only the compression files:

```bash
git add agent/context_compressor.py agent/agent_init.py gateway/run.py \
  tests/agent/test_context_compressor.py tests/gateway/test_session_hygiene.py
git diff --cached --name-only
git commit -m "fix(context): use hybrid compression threshold"
```

Push to the user's private remote/branch when that is the active branch strategy, then read back with `git ls-remote`.
