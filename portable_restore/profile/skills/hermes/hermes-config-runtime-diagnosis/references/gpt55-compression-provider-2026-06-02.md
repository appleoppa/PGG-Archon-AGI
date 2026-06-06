# GPT-5.5 Compression Provider Stabilization (2026-06-02)

## Trigger

Use when Hermes reports repeated context/compression failures, compression summary failures, context bloat, premature gateway session hygiene, or user asks to stabilize context compression.

## Root Cause Pattern

Observed on default profile:

- `compression.hygiene_hard_message_limit=100` caused gateway session hygiene to force compression by message count even when token usage was below the intended token threshold.
- Logs showed examples like `113 messages, ~88,443 tokens ... auto-compressing (threshold: absolute 150,000...)`, meaning message count, not token pressure, was the real trigger.
- `auxiliary.compression.timeout=60` was too short for long-context summarization under provider/network latency.
- `auxiliary.compression.provider=custom:deepseek_v4_flash` smoke-tested successfully, but multi-LLM audit judged GPT-5.5 more stable for high-fidelity long-context summaries.

## Durable Fix Shape

Back up `~/.hermes/config.yaml`, then set:

```yaml
compression:
  hygiene_hard_message_limit: 400
  absolute_threshold_tokens: 150000
  threshold_safety_percent: 0.7

auxiliary:
  compression:
    provider: custom:gpt55_5yuantoken
    model: gpt-5.5
    timeout: 180
    context_length: 1050000
```

Keep `absolute_threshold_tokens` and `threshold_safety_percent`; do not remove the hybrid token threshold.

## Verification Recipe

Run from `~/.hermes/hermes-agent`:

```bash
venv/bin/python - <<'PY'
import sys, pathlib, yaml, time
from dotenv import load_dotenv
load_dotenv('/Users/appleoppa/.hermes/.env')
sys.path.insert(0, '.')
from agent.auxiliary_client import call_llm
from agent.context_compressor import ContextCompressor, _SUMMARY_INPUT_MAX_CHARS
cfg = yaml.safe_load(pathlib.Path('/Users/appleoppa/.hermes/config.yaml').read_text())
print('READBACK', cfg['compression']['hygiene_hard_message_limit'], cfg['auxiliary']['compression'])
c = ContextCompressor('gpt-5.5', threshold_percent=cfg['compression']['threshold'], absolute_threshold_tokens=cfg['compression']['absolute_threshold_tokens'], threshold_safety_percent=cfg['compression']['threshold_safety_percent'], summary_target_ratio=cfg['compression']['target_ratio'], quiet_mode=True, config_context_length=1050000)
print('COMPRESSOR', _SUMMARY_INPUT_MAX_CHARS, c.threshold_tokens, c.tail_token_budget, c.max_summary_tokens)
t = time.time()
r = call_llm(task='compression', messages=[{'role':'user','content':'请只回复：GPT5.5 compression smoke OK'}], max_tokens=80)
print('AUX_COMPRESSION_GPT55_OK elapsed=%.1fs content=%s' % (time.time()-t, (r.choices[0].message.content or '').strip()))
PY

venv/bin/python -m pytest tests/agent/test_context_compressor.py tests/gateway/test_session_hygiene.py -q
hermes gateway restart
hermes gateway status
```

Expected evidence:

- Config readback shows `hygiene_hard_message_limit=400`, provider `custom:gpt55_5yuantoken`, model `gpt-5.5`, timeout `180`, context length `1050000`.
- GPT-5.5 compression smoke returns `GPT5.5 compression smoke OK`.
- Targeted tests pass (observed: `122 passed`).
- Gateway restarts and Feishu reconnects.

## Pitfalls

- Do not diagnose this as a broken DeepSeek provider solely because compression was noisy; DeepSeek smoke may pass. The practical fix is reducing premature compression and using GPT-5.5 for higher-fidelity summaries.
- Do not lower hard message limit to 100 for active Feishu/gateway sessions; it causes frequent count-based compression before true token pressure.
- GPT/Claude custom providers must remain on Responses API (`api_mode: codex_responses`); do not route GPT-5.5 through `/v1/chat/completions`.
- After any change, update `/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json` with `python -m apex_god.evolution_manifest --update`.
