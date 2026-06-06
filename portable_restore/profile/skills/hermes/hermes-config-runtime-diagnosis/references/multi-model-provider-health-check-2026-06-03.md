# Multi-Model Provider Health Check — 2026-06-03

## Test script pattern

Source keys from `~/.hermes/.env`, then call each provider's `/chat/completions` endpoint:

```bash
source ~/.hermes/.env && python3 -c "
import os, json, urllib.request, ssl, time
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

providers = [
    ('name', 'base_url', 'model', 'KEY_ENV_VAR'),
    # ... enumerate from config.yaml
]
for name, base, model, key_env in providers:
    key = os.environ.get(key_env, '')
    if not key:
        print(f'❌ {name}: key not set'); continue
    url = f'{base}/chat/completions'
    payload = json.dumps({'model': model, 'messages': [{'role':'user','content':'Reply OK'}], 'max_tokens': 500, 'temperature': 0}).encode()
    headers = {'Content-Type':'application/json','Authorization':f'Bearer {key}'}
    try:
        t0 = time.time()
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = json.loads(resp.read())
            dt = time.time()-t0
            reply = body.get('choices',[{}])[0].get('message',{}).get('content','').strip()
            # Also check reasoning_content for reasoning models
            reasoning = body.get('choices',[{}])[0].get('message',{}).get('reasoning_content','').strip()
            if not reply and reasoning:
                print(f'⚠️  {name}: {dt:.1f}s → content empty, reasoning={reasoning[:40]}')
            else:
                print(f'✅ {name}: {dt:.1f}s → \"{reply[:60]}\"')
    except Exception as e:
        print(f'❌ {name}: {e}')
"
```

## Reasoning model empty-content pitfall

**Models affected**: DeepSeek-V4-Flash, MiMo-v2.5-Pro, and any model using chain-of-thought / reasoning tokens.

**Symptom**: HTTP 200, `choices[0].message.content=""`, `finish_reason=length`.

**Root cause**: `max_tokens` covers BOTH reasoning tokens and output tokens. With `max_tokens=10`:
- DeepSeek: 10/10 tokens → reasoning, 0 → content
- MiMo: 9/10 tokens → reasoning, 1 → content (still empty)

**Fix**: Use `max_tokens≥500` when testing. In production, Hermes config typically uses much higher limits so this only affects ad-hoc test scripts.

**Detection**: Check `choices[0].message.reasoning_content` (non-standard field) — if it's non-empty while `content` is empty, the model consumed all budget on reasoning.

## Known providers and their API modes (as of 2026-06-03)

| Provider | Model | API Mode | Notes |
|----------|-------|----------|-------|
| gpt55_5yuantoken | gpt-5.5 | codex_responses | Via chuangagent.eu.cc |
| claude_opus46_5yuantoken | claude-opus-4-6 | codex_responses | Via chuangagent.eu.cc |
| deepseek_v4_flash | deepseek-v4-flash | chat_completions | Reasoning model, uses reasoning_content |
| mimo_v25_pro_auditor | mimo-v2.5-pro | chat_completions | Reasoning model, uses reasoning_content |
| agnes_ai | agnes-2.0-flash | chat_completions | Fast, ~1s latency |

## execute_code pitfall

`execute_code` runs in a sandboxed subprocess that does NOT inherit shell environment variables. API keys from `~/.hermes/.env` are not available. Always use `terminal` with explicit `source ~/.hermes/.env &&` prefix when testing providers.
