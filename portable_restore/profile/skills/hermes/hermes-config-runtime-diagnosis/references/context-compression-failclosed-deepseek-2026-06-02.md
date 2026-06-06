# Context Compression Fail-Closed + DeepSeek Stabilization (2026-06-02)

## Trigger

Use when the user reports that context still breaks after compression-provider tuning, or logs show:

- `Failed to generate context summary: Request timed out`
- `Codex auxiliary Responses stream interrupted`
- `stream_read_error`
- `Cloudflare 502` from GPT/Claude Responses API endpoint
- user-visible context loss after auto-compression

## Root Cause

Verified code path in `agent/context_compressor.py`:

- `_generate_summary()` returns `None` when the auxiliary compression LLM fails.
- If `compression.abort_on_summary_failure=false`, `compress()` calls `_build_static_fallback_summary(...)`, inserts a deterministic fallback marker, and drops the middle window.
- This fail-open behavior preserves liveness but can break context fidelity, especially in long PGG Archon / AGI / legal workflows.

Default-profile evidence on 2026-06-02:

- `auxiliary.compression=custom:gpt55_5yuantoken/gpt-5.5`
- `timeout=180`
- logs contained timeout / Responses stream interrupted / Cloudflare 502 / stream_read_error
- user still observed context/compression failures

## LLM Audit Consensus

Real calls:

- GPT-5.5: recommended P0 `abort_on_summary_failure=true` + switch compression provider away from unstable GPT path; P1 multi-provider fallback.
- DeepSeek V4 Flash: recommended switching compression provider to `deepseek_v4_flash`.
- MIMO V2.5 Pro: recommended DeepSeek for immediate stabilization, fallback chain later.
- Agnes 2.0 Flash: recommended provider B (DeepSeek) and avoiding silent context dropping.
- Claude Opus 4-6 returned empty content; excluded from conclusion.

## Safe Fix

Set config:

```yaml
compression:
  abort_on_summary_failure: true
  hygiene_hard_message_limit: 400
  absolute_threshold_tokens: 150000
  threshold_safety_percent: 0.7

auxiliary:
  compression:
    provider: custom:deepseek_v4_flash
    model: deepseek-v4-flash
    timeout: 180
    context_length: 1000000
```

Do **not** solve this by blindly raising token thresholds or `max_turns`; that delays compression and can worsen context-overflow failures.

## Verification

```bash
cd ~/.hermes/hermes-agent
venv/bin/python - <<'PY'
import sys, pathlib, yaml, time
from dotenv import load_dotenv
load_dotenv('/Users/appleoppa/.hermes/.env')
sys.path.insert(0,'.')
from agent.auxiliary_client import call_llm
from agent.context_compressor import ContextCompressor
cfg=yaml.safe_load(pathlib.Path('/Users/appleoppa/.hermes/config.yaml').read_text())
print(cfg['compression']['abort_on_summary_failure'])
print(cfg['auxiliary']['compression']['provider'], cfg['auxiliary']['compression']['model'])
r=call_llm(task='compression', messages=[{'role':'user','content':'请只回复：DeepSeek compression failclosed smoke OK'}], max_tokens=80)
print((r.choices[0].message.content or '').strip())
c=ContextCompressor('test', quiet_mode=True, abort_on_summary_failure=True, config_context_length=1000000)
msgs=[{'role':'system','content':'sys'}]+[{'role':'user' if i%2==0 else 'assistant','content':'x'*500} for i in range(20)]
c._generate_summary=lambda turns, focus_topic=None: None
out=c.compress(msgs, current_tokens=200000)
assert out == msgs and c._last_compress_aborted and c._last_summary_dropped_count == 0
print('FAILCLOSED_OK')
PY
venv/bin/python -m pytest tests/agent/test_context_compressor.py tests/gateway/test_session_hygiene.py -q
hermes gateway restart
hermes gateway status
```

Observed evidence:

- DeepSeek compression smoke succeeded in 2.4s.
- Fail-closed simulation preserved all messages and set `_last_compress_aborted=True` / dropped count `0`.
- Targeted tests: `122 passed`.

## Next-stage P1

P1 was implemented after a real bug was found in `agent/auxiliary_client.py`: `_resolve_single_provider()` passed `base_url` / `api_key` to `resolve_provider_client()`, whose actual parameters are `explicit_base_url` / `explicit_api_key`. This made `auxiliary.<task>.fallback_chain` entries fail with `TypeError` when exercised. The fix is surgical and covered by `tests/agent/test_auxiliary_client.py::TestConfiguredFallbackChain::test_resolve_single_provider_uses_explicit_endpoint_kwargs`.

Default compression fallback chain now uses:

1. primary: `custom:deepseek_v4_flash` / `deepseek-v4-flash`
2. fallback 1: `custom:gpt55_5yuantoken` / `gpt-5.5`
3. fallback 2: `custom:agnes_ai` / `agnes-2.0-flash`

MIMO is kept for audit, not compression fallback, because live smoke showed it did not reliably follow the exact concise compression-smoke instruction. Keep fail-closed semantics: no provider failure may silently drop the middle context window.
