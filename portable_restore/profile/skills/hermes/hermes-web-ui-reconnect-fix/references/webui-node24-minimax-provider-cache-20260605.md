# Web UI Node v24 + stale MiniMax provider cache repair (2026-06-05)

## Trigger

Use when Hermes Web UI task execution shows:

```text
Error code: 401 - {'type':'authentication_error','message':'invalid api key'}
```

and logs show the run used:

```text
provider=minimax
base_url=https://api.minimax.io/anthropic
model=MiniMax-M3
```

This is not the configured OpenAI-compatible MiniMax-M3 provider. It is a stale/built-in Web UI/provider catalog route.

## Correct target route

```text
provider=custom:minimax_m3
base_url=https://api.minimax.chat/v1
model=MiniMax-M3
key_env=MINIMAX_API_KEY
```

## Diagnosis checklist

1. Verify Web UI health and actual Node version:
   - `curl -fsS http://127.0.0.1:8648/health`
   - Expect `node_version` to match intended runtime, e.g. `24.14.1` after Node upgrade.
2. Check live process path:
   - Web UI under launchd should be `/usr/local/bin/node .../hermes-web-ui/dist/server/index.js` when intentionally using Node v24.
3. Read Web UI bridge logs for actual provider:
   - `~/.hermes-web-ui/logs/bridge.log`
   - `~/.hermes/logs/agent.log` / `errors.log`
4. Inspect Web UI catalog/config without printing secrets:
   - `~/.hermes-web-ui/config.json`
   - `~/.hermes-web-ui/cache/provider-model-catalog.json`
   - `~/.hermes/auth.json`
   - `~/.hermes/models_dev_cache.json`

## Repair pattern

1. Back up:
   - `~/.hermes/auth.json`
   - `~/.hermes/models_dev_cache.json`
   - `~/.hermes-web-ui/cache/provider-model-catalog.json`
2. Remove only stale built-in `minimax` / `minimax-cn` / `api.minimax.io/anthropic` records.
3. Preserve `custom:minimax_m3` and `https://api.minimax.chat/v1`.
4. Delete Web UI provider catalog cache so it regenerates.
5. Restart Web UI and bridge.
6. Verify the regenerated catalog has:

```text
api.minimax.io/anthropic = False
builtin_provider_minimax = False
custom:minimax_m3 = True
```

## Node upgrade pitfall

If the user upgraded Node because Web UI requested it, do not permanently roll back to Hermes-bundled Node v22 as the final answer. A v22 restart can be a short stopgap, but the closed-loop fix is to verify Web UI under the intended upgraded Node and update/confirm launchd:

```text
~/Library/LaunchAgents/ai.hermes.webui.plist ProgramArguments[0] = /usr/local/bin/node
launchctl list ai.hermes.webui -> Program=/usr/local/bin/node
health.node_version -> 24.x
```

## Two-version Node unification pattern

When `/usr/local/bin/node` is upgraded but `~/.hermes/node/bin/node` or `~/.local/bin/node` still points to an older bundled runtime, Web UI can appear fixed in one start mode and broken in another. Close the loop by unifying paths instead of merely restarting:

1. Back up current configs and old runtime under `~/.hermes/workspace/backups/`.
2. Confirm all candidate paths and versions:
   - `/usr/local/bin/node`
   - `~/.hermes/node/bin/node`
   - `~/.local/bin/node`
   - corresponding `npm` / `npx` paths.
3. If the upgraded runtime is the intended baseline, archive the old bundled runtime, e.g. `~/.hermes/node -> ~/.hermes/node.v22.disabled-<timestamp>`.
4. Create compatibility symlinks so old callers still resolve to the new runtime:

```text
~/.hermes/node -> /usr/local
~/.local/bin/node -> /usr/local/bin/node
~/.local/bin/npm  -> /usr/local/bin/npm
~/.local/bin/npx  -> /usr/local/bin/npx
```

5. Update launchd plist `ProgramArguments[0]` to `/usr/local/bin/node`.
6. Restart with `launchctl kickstart -k gui/$(id -u)/ai.hermes.webui`.
7. Verify:

```text
health.node_version = 24.x
all node paths -> same 24.x
all npm paths -> same npm version
provider catalog: api.minimax.io/anthropic False, custom:minimax_m3 True
```

Do not call the task complete while Web UI is stopped; start it and read back `/health`.

## Boundaries

- Do not print API keys.
- Do not delete valid `MINIMAX_API_KEY` env entries.
- Do not infer provider health from catalog presence; verify logs and health readback.
- This repairs Web UI/provider routing, not Hermes core scheduler/security boundary.
- When hard-banning built-in MiniMax endpoints in the Web UI bundle, do not use a broad base URL substring such as `includes("api.minimax")`; it also matches the valid custom OpenAI-compatible endpoint `https://api.minimax.chat/v1` and hides `custom:minimax_m3` from `/api/hermes/available-models`. Ban only exact built-in Anthropic endpoints such as `api.minimax.io/anthropic` and `api.minimaxi.com/anthropic`, while preserving `custom:minimax_m3` and `api.minimax.chat`.
