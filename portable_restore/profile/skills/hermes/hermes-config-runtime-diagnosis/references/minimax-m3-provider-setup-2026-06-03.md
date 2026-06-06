# MiniMax M3 Provider Setup — 2026-06-03

## Scope

Use this note when configuring MiniMax `MiniMax-M3` as a Hermes custom provider in the active/default profile.

## Known-good provider block

Add the provider in both `providers` and `custom_providers` so Hermes CLI/runtime and picker-style code paths can discover it:

```yaml
providers:
  minimax_m3:
    api_mode: chat_completions
    base_url: https://api.minimax.chat/v1
    default_model: MiniMax-M3
    key_env: MINIMAX_API_KEY
    model: MiniMax-M3
    models:
      MiniMax-M3:
        context_length: 1000000
    name: minimax_m3
    context_length: 1000000

custom_providers:
  - api_mode: chat_completions
    base_url: https://api.minimax.chat/v1
    default_model: MiniMax-M3
    key_env: MINIMAX_API_KEY
    model: MiniMax-M3
    models:
      MiniMax-M3:
        context_length: 1000000
    name: minimax_m3
    context_length: 1000000
```

Store the key in `~/.hermes/.env`:

```bash
MINIMAX_API_KEY=sk-...
```

Never print the full key; report only presence/prefix/suffix if necessary.

## Verification ladder

1. Back up `~/.hermes/config.yaml` and `~/.hermes/.env` before writing.
2. Verify model entitlement:
   - `GET https://api.minimax.chat/v1/models`
   - Require HTTP 200 and `MiniMax-M3` in the returned model ids.
3. Verify direct chat-completions:
   - `POST https://api.minimax.chat/v1/chat/completions`
   - payload includes `model: MiniMax-M3`, `messages`, `max_tokens >= 50` for smoke tests.
4. Verify Hermes runtime path:
   ```bash
   hermes -z 'Return exactly: OK' --provider custom:minimax_m3 -m MiniMax-M3 --cli
   ```
   Expected visible output: `OK`.

## Pitfalls

- MiniMax M3 is available through the OpenAI-compatible chat-completions endpoint at `https://api.minimax.chat/v1/chat/completions`; do not configure it as Responses API.
- The model may emit reasoning/thinking text in direct API responses when asked for tiny outputs. Do not treat that as provider failure if Hermes CLI returns the requested visible answer.
- Terminal commands do not automatically load `~/.hermes/.env`; direct verification scripts should parse/source `.env` explicitly.
- If a user pasted a live API key in chat, recommend rotating it after configuration succeeds.
