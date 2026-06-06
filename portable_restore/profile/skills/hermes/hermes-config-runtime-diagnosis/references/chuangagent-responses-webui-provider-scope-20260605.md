# ChuangAgent Responses + Web UI Built-in Provider Scope — 2026-06-05

## Scope

Session-specific evidence for Hermes provider configuration and Web UI model catalog repairs involving:

- `gpt55_5yuantoken`
- `claude_opus46_5yuantoken`
- Web UI built-in `minimax` / `minimax-cn` / `copilot`
- User-defined `custom:minimax_m3`

## Lessons

### 1. Do not downgrade GPT/Claude ChuangAgent providers to chat_completions

User rule: GPT/Claude custom providers must not use `/v1/chat/completions`; keep `api_mode: codex_responses` / Responses API.

Observed behavior:

- Direct `curl https://chuangagent.eu.cc/v1/responses` for `gpt-5.5` can return HTTP 200, `status=completed`, and `output=[]`.
- This direct curl symptom is not sufficient to declare GPT unusable and is not a reason to change Hermes config back to `chat_completions`.
- Hermes' own `codex_responses` adapter can still succeed.

Verified command shape:

```bash
/Users/appleoppa/.local/bin/hermes -z 'Return exactly: OK' \
  --provider custom:gpt55_5yuantoken \
  --model gpt-5.5
```

Expected verification result:

```text
OK
```

Claude repaired configuration:

- Provider key: `custom:claude_opus46_5yuantoken`
- Model: `claude-opus-4-6`
- Base URL: `https://chuangagent.eu.cc`  (NOTE: root only — NO `/v1` suffix)
- API mode: `codex_responses`
- Key env: `CLAUDE_OPUS47_5YUANTOKEN_API_KEY`

**Claude vs GPT base_url distinction:**

| Model | base_url | Why |
|-------|----------|-----|
| GPT-5.5 | `https://chuangagent.eu.cc/v1` | ChuangAgent routes GPT through `/v1` subpath |
| Claude | `https://chuangagent.eu.cc` | ChuangAgent routes Claude from root — adding `/v1` causes 502 |

Do NOT set Claude to the same base_url as GPT. Use root only.

Verified command shape:

```bash
/Users/appleoppa/.local/bin/hermes -z 'Return exactly: OK' \
  --provider custom:claude_opus46_5yuantoken \
  --model claude-opus-4-6
```

Expected verification result:

```text
OK
```

### 2. Web UI built-in provider removal must preserve custom providers

When the user says to delete built-in MiniMax/GitHub provider entries from `hermes-web-ui`, do not remove or ban the user-defined `custom:minimax_m3` provider unless explicitly requested.

Correct distinction:

- Remove/hide/disable built-ins: `minimax`, `minimax-cn`, `copilot`, optionally `github` / `github-copilot` aliases.
- Preserve custom provider: `custom:minimax_m3`.

Verification targets:

- `~/.hermes-web-ui/config.json.modelVisibility` should still include `custom:minimax_m3` if configured by the user.
- `hiddenProviders` and `disabledProviders` may include built-ins but should not include `custom:minimax_m3`.
- `~/.hermes-web-ui/cache/provider-model-catalog.json` should not include built-in `minimax|`, `minimax-cn|`, `copilot|`, or `githubcopilot.com` entries, but may include `custom:minimax_m3|https://api.minimax.chat/v1|all`.
- Runtime catalog filters in `dist/server/index.js`, if patched, must ban built-in provider ids and built-in endpoint URLs without banning the custom provider key.

## Pitfall: ChuangAgent upstream 502 — raw HTTP fails, Hermes CLI succeeds

ChuangAgent's upstream GPT/Claude backend is intermittently overloaded, returning Cloudflare 502 (`origin_bad_gateway`) on direct HTTP requests. This is a recurring pattern (observed 2026-06-04, 2026-06-05, 2026-06-06).

**Symptom:**
- Direct `curl` / `urllib` call to `https://chuangagent.eu.cc/v1/responses` → HTTP 502
- Same for `/v1/chat/completions` → HTTP 502
- Hermes CLI `codex_responses` adapter → ✅ OK (gets through via its own retry/handshake logic)

**Diagnosis:** The root page `https://chuangagent.eu.cc/` returns HTTP 200 (gateway layer alive), but the generation upstream is overloaded. 5+ retries across both primary and fallback endpoints may still all return 502.

**Fix — do NOT downgrade to chat_completions.** The fix is a retry wrapper that routes through the Hermes CLI adapter:

```
/Users/appleoppa/.hermes/scripts/gpt55_retry_adapter.sh
```

Usage:
```bash
# Mode cli (default, recommended): goes through Hermes CLI adapter
gpt55_retry_adapter.sh cli "your prompt"

# Mode raw: direct HTTP with 5 retries (may all fail if upstream down)
gpt55_retry_adapter.sh raw "your prompt"
```

The CLI mode is the only reliable path during upstream outages. All tool-level GPT-5.5 calls should route through the Hermes CLI rather than raw HTTP.

**Fallback endpoint:** `https://5yuantoken.org/v1` — currently also returns 502 when ChuangAgent is overloaded (they share upstream infrastructure). Do not assume it works when primary fails.

## Pitfall

A broad string filter such as `if 'minimax' in provider` is wrong: it catches both built-in `minimax` and user-defined `custom:minimax_m3`. Filter exact provider ids and/or built-in endpoint URLs instead.

For ChuangAgent GPT/Claude in Hermes Web UI, fixing `~/.hermes/config.yaml` alone is not enough. The Web UI server bundle's `/api/hermes/available-models` path must propagate custom provider `api_mode` and `key_env` from `custom_providers` into model groups. If those fields are dropped, the UI/coding-agent launch path can display or pass the default `chat_completions` even when Hermes CLI uses `codex_responses`. Verified repair pattern: add `custom:claude_opus46_5yuantoken` to the Web UI custom-provider catalog allowlist; include `api_mode:p.api_mode` and `key_env:p.key_env` in the custom provider map; expose `api_mode/key_env` at group top-level and `model_meta`; preserve them during profile group merge; run `node -c`, restart Web UI/gateway, and verify both config readback and real `hermes -z ... --provider custom:gpt55_5yuantoken` / `custom:claude_opus46_5yuantoken` return OK.

## Correct report boundary

Report these as separate statuses:

- Built-in provider removed/hidden from Web UI.
- User-defined custom provider preserved and verified.
- Hermes core provider config changed or not changed.

Do not conflate Web UI catalog cleanup with global Hermes core provider deletion.
