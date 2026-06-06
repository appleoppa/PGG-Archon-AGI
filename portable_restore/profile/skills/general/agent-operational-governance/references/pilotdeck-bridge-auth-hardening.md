# PilotDeck GPT Bridge Auth Hardening Pattern

Use when PilotDeck uses a local Hermes/PilotDeck OpenAI-compatible bridge for GPT collaboration while MIMO remains the main tools-capable model.

## Durable pattern

1. Keep model roles fixed:
   - MIMO: only tools-capable main `agent/router/fallback/memory/tokenSaver` model.
   - GPT: no-tools advisory/collaboration model via local bridge.
   - Agnes: chat-only/no-tools backup.
2. Before hardening, create backups of both bridge code and `pilotdeck.yaml`.
3. Add optional bearer auth to the bridge:
   - read token from `PILOTDECK_LLM_BRIDGE_TOKEN`;
   - require `Authorization: Bearer <token>` for `/v1/models` and `/v1/chat/completions`;
   - keep `/health` unauthenticated for liveness probes;
   - keep bridge bound to `127.0.0.1` only.
4. Store the token under PilotDeck hidden home, not Home root:
   - `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/.env`
   - `pilotdeck.yaml` provider `apiKey`
   - permissions `0600`.
5. If startup script sources `.env`, use `set -a; . .env; set +a` so the token is exported to the Python bridge subprocess. Plain `. .env` without export is insufficient.
6. Restart only the bridge first, then validate auth; restart PilotDeck gateway/UI after config changes.
7. Add the auth behavior to the invariant checker so a future session catches regressions.

## Verification checklist

Run real HTTP checks, not just file reads:

```text
/health                         no auth => 200
/v1/models                      no auth => 401
/v1/models                      with configured token => 200
/v1/chat/completions            no auth => 401
/v1/chat/completions            with configured token => 200 and model returns a sentinel
```

Then verify:

```text
MIMO supports tools = true
GPT supports tools = false
Agnes supports tools = false
agent/router/fallback/memory/tokenSaver all point to MIMO
~/.pilotdeck symlink points to ~/.pilotdeck-agi/home/.pilotdeck
```

## Pitfalls

- Config API or UI may mask secrets as `*****`; use local file/invariant checks for presence/length/prefix, but never print the token.
- A successful `/health` check only proves liveness, not auth enforcement or GPT usability.
- If no-auth requests still return 200 after code changes, check whether the token was exported to the bridge process; this often means `.env` was sourced without `set -a` or explicit `export`.
- Do not put GPT into fallback/router execution chains just because bridge auth works; GPT remains advisory-only/no-tools.
