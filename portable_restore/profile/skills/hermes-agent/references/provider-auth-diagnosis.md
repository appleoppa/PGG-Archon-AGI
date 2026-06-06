# Provider Authentication Diagnosis

## Quick Checklist — LLM not responding / 401 errors

1. **Which provider is actually failing?**
   - CLI session: if the CLI works but web UI doesn't, the problem is NOT the key itself — find the provider with the bad key.
   - Web UI: check `~/.hermes-web-ui/logs/server.log` for `available-models https://... returned 401`
   - Gateway: check `~/.hermes/logs/gateway.log` for `Empty response` / `retry` / error patterns
   - Cron: check logs for `empty_response_exhausted`

2. **Test the API key directly**
   ```bash
   KEY=$(cat ~/.hermes/.env | grep "^<KEY_ENV>=" | sed 's/^<KEY_ENV>=//')
   curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $KEY" https://<provider>/v1/models
   ```
   - 200 = key works → Hermes config issue (wrong key_env mapping, wrong base_url, wrong api_mode)
   - 401 = key is invalid/expired → needs replacement
   - 403/502 = key works but endpoint rejects the model/account type

3. **Check key_env alignment between config and .env**
   ```yaml
   # config.yaml — custom provider
   providers:
     my_provider:
       key_env: SOME_API_KEY  # <-- must match the .env variable name exactly
   ```
   ```bash
   # .env — must have the exact variable name
   SOME_API_KEY=sk-...
   ```

4. **Parallel provider duplication**
   If both built-in and custom providers exist for the same service (e.g. `provider: deepseek` + `providers: deepseek_v4_flash`), they may use different key_env values. Check both. Unify to one:
   - Prefer custom provider (more explicit, full control)
   - Update: main `config.yaml` → `model.provider: custom:<provider_name>`
   - Update: profile `config.yaml` (same change)
   - Update: `~/.hermes-web-ui/config.json` → change provider key in modelVisibility
   - Clean up: comment out the unused key_env variable in `.env`

## Web UI Specific

The web UI (`hermes-web-ui`) lists available models at startup via `GET /v1/models` on each configured provider's base_url. If a provider returns 401, the web UI shows those models as unavailable.

Log location: `~/.hermes-web-ui/logs/server.log`
Key log line to grep: `available-models https://... returned 401`

The web UI uses an **agent bridge** (IPC sockets) to communicate with the Hermes gateway. Bridge workers use the profile config to determine provider/model. Each profile (default, deepseek, minimax) runs its own bridge worker.

## Common Culprits

| Symptom | Likely cause |
|---------|-------------|
| `available-models 401` on web UI | Provider API key expired/invalid |
| CLI works, web UI doesn't | Different provider config between CLI and web UI (profile mismatch) |
| Only gpt-5.5 fails (not deepseek/minimax) | The 5yuantoken/OpenRouter/free-tier key expired — not a Hermes config bug |
| Compression/session_search hangs | `auxiliary.*` providers use a different model that may have different auth |
