# gpt55 working base_url = https://chuangagent.eu.cc/v1/chat/completions — 2026-06-04

## Symptom

When a custom provider entry uses the `gpt55_5yuantoken` registry key (i.e.
`provider: custom:gpt55_5yuantoken`), naive endpoint guessing from the
`.env` key name `GPT55_5YUANTOKEN_API_KEY` produces these failure modes:

| Endpoint | Mode | Result |
|---|---|---|
| `https://api.5yuantoken.com/v1/chat/completions` | chat | SSL EOF (LibreSSL 2.8.3 ↔ upstream TLS handshake fail) |
| `https://api.5yuantoken.com/v1/responses` | responses | SSL EOF |
| `https://api5.5yuantoken.com/v1/chat/completions` | chat | SSL EOF |
| `https://chuangapi.5yuantoken.com/v1/chat/completions` | chat | SSL EOF |
| `https://api.minimax.chat/v1/chat/completions` | chat | HTTP 401 (`login fail: 1004`) |
| `https://chuangagent.eu.cc/v1/chat/completions` | chat | **HTTP 200, 4-char "pong"** |
| `https://chuangagent.eu.cc/v1/responses` | responses | HTTP 200, `text_chars=0` (proxy quirk — use chat path instead) |

The failures are reproducible with `verify=False` (still SSL EOF) and persist
across `requests` 2.x / urllib3 2.x; the root cause is on the upstream side,
not the local LibreSSL.

## Authoritative source: `~/.hermes/config.yaml`

The custom-provider block in `~/.hermes/config.yaml` already declares:

```yaml
custom_providers:
  - name: gpt55_5yuantoken
    base_url: https://chuangagent.eu.cc/v1
    default_model: gpt-5.5
    model: gpt-5.5
```

`grep -E 'base_url|GPT55|gpt55|gpt-5' ~/.hermes/config.yaml` will reveal the
true endpoint without trial-and-error.

## Verified fix (smoke recipe)

```python
import os, json, requests
from pathlib import Path

for line in (Path.home() / ".hermes" / ".env").read_text(errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

key = os.environ["GPT55_5YUANTOKEN_API_KEY"]
h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
pl = {"model": "gpt-5.5", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 64}
r = requests.post("https://chuangagent.eu.cc/v1/chat/completions", headers=h, json=pl, timeout=30)
print(r.status_code, (r.json().get("choices") or [{}])[0].get("message", {}).get("content"))
# 200 pong
```

A 5-LLM collaboration (`DeepSeek + MiMo + Agnes + MiniMax + gpt5.5` → 5/5
each = 25/25 real calls) using this base_url is the full verification record.

## When to use this reference

- Any time a `gpt55_5yuantoken` (or similar `*_5yuantoken` custom provider)
  smoke call SSL-EOFs or 401s on guessed endpoints, read `config.yaml` and
  use the registered `base_url` directly.
- For Claude ChuangAgent the same shape applies: the working base_url comes
  from `custom_providers[].base_url`, not from `.env` key names.
- For reasoning model callers, also use the `references/gpt55-codex-responses-token-param-20260603.md`
  rule of `max_tokens` (not `max_output_tokens`) on the `/responses` path.

## Boundaries

- Do not print the API key value in reports; report `key_env=...`, `len(key)`, and `http_status` only.
- Do not promote `chuangagent.eu.cc` to the official ChuangAgent origin
  for any other provider; verify each custom provider's `config.yaml` block.
- Do not switch GPT/Claude to `/chat/completions` if the original config
  declares `api_mode: responses`; that was a separate fix for empty output
  and lives in `gpt55-codex-responses-token-param-20260603.md`.
