# ChuangAgent GPT/Claude Responses + Web UI api_mode propagation — UI-verified 2026-06-05

## Trigger

Use when GPT/Claude ChuangAgent providers appear in Hermes Web UI as `/v1/chat/completions`, route expensively through chat-completions, or Claude/GPT tests disagree between CLI and Web UI.

## Durable lesson

For this user's setup, GPT and Claude ChuangAgent providers are Responses API providers. Do not downgrade to `chat_completions` to make a naive curl test look better.

Known-good provider shape:

```text
custom:gpt55_5yuantoken
  model: gpt-5.5
  base_url: https://chuangagent.eu.cc/v1
  key_env: GPT55_5YUANTOKEN_API_KEY
  api_mode: codex_responses

custom:claude_opus46_5yuantoken
  model: claude-opus-4-6
  base_url: https://chuangagent.eu.cc/v1
  key_env: CLAUDE_OPUS47_5YUANTOKEN_API_KEY
  api_mode: codex_responses
```

`https://chuangagent.eu.cc/responses` root-path direct probes may fail through Cloudflare; Hermes' working base is `https://chuangagent.eu.cc/v1`, which resolves to `/v1/responses` for codex_responses.

## Critical Web UI pitfall

Fixing `~/.hermes/config.yaml` alone is insufficient. Web UI can still display or pass `chat_completions` if `/api/hermes/available-models` drops custom provider metadata.

Required Web UI bundle properties:

- `custom:gpt55_5yuantoken` present.
- `custom:claude_opus46_5yuantoken` present in custom-provider catalog allowlist.
- custom provider map carries `api_mode:p.api_mode` and `key_env:p.key_env`.
- group payload exposes/preserves `api_mode` and `key_env` at top-level or `model_meta`.
- profile group merge preserves `api_mode/key_env`.

Verify bundle markers instead of trusting UI labels:

```bash
python3 - <<'PY'
from pathlib import Path
s=(Path.home()/'.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js').read_text(errors='ignore')
for term in ['custom:gpt55_5yuantoken','custom:claude_opus46_5yuantoken','api_mode:p.api_mode','key_env:p.key_env','api_mode:H.api_mode','key_env:H.key_env']:
    print(term, s.find(term))
PY
```

## Verification ladder

1. Read `~/.hermes/config.yaml`; both `providers.*` and `custom_providers[]` entries must show `api_mode: codex_responses`.
2. Run `node -c ~/.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js` after any Web UI bundle patch.
3. Restart Web UI and gateway.
4. Run CLI smoke through the real Hermes binary:

```bash
/Users/appleoppa/.local/bin/hermes -z 'Return exactly: OK_GPT_CODEX_RESPONSES_FINAL' --provider custom:gpt55_5yuantoken --model gpt-5.5 --cli
/Users/appleoppa/.local/bin/hermes -z 'Return exactly: OK_CLAUDE_CODEX_RESPONSES_FINAL' --provider custom:claude_opus46_5yuantoken --model claude-opus-4-6 --cli
```

5. Ask/observe UI-side model selector after refresh/new session; old sessions may retain stale provider metadata.

## User correction captured

The user reported that although prior CLI tests passed, Web UI still showed GPT as `/v1/chat/completions`, causing high cost. After config + Web UI metadata propagation fix, user confirmed the UI-side test was effective. Future sessions must treat UI picker/runtime metadata as a separate completion gate from CLI smoke.
