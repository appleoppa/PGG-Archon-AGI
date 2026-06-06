# Web UI built-in provider hard-ban pattern — 2026-06-05

## Trigger

Use when Hermes Web UI repeatedly routes to or probes unwanted built-in providers even after `~/.hermes-web-ui/config.json` hides/disables them. Typical symptoms:

- `available-models https://api.githubcopilot.com/v1/models returned 404`
- `available-models https://api.minimax.chat/v1/models returned 401`
- `available-models https://api.minimax.io/anthropic/v1/models returned 401`
- bridge/session log shows `provider=minimax` or `Provider: minimax` although the intended provider is custom-only.

## Durable lesson

Hiding providers in `config.json` is not always enough. Web UI can regenerate model catalog entries from:

1. `~/.hermes-web-ui/config.json` visibility/disabled lists;
2. `~/.hermes-web-ui/cache/provider-model-catalog.json`;
3. Hermes core `custom_providers[]`;
4. hardcoded built-in provider catalog inside the installed `hermes-web-ui/dist/server/index.js` bundle;
5. old running Web UI process still occupying port 8648 after launchd restart.

## Safe repair sequence

1. Back up before modification:

```bash
cp ~/.hermes-web-ui/config.json ~/.hermes-web-ui/config.json.bak_remove_builtin_<timestamp>
cp ~/.hermes-web-ui/cache/provider-model-catalog.json ~/.hermes-web-ui/cache/provider-model-catalog.json.bak_remove_builtin_<timestamp>
cp ~/.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js ~/.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js.bak_remove_builtin_<timestamp>
```

2. In `~/.hermes-web-ui/config.json`:

- remove unwanted providers from `modelVisibility`;
- add them to both `hiddenProviders` and `disabledProviders`;
- keep `copilotEnabled=false`.

For the MiniMax/GitHub incident, the banned set was:

```text
minimax
minimax-cn
copilot
github
github-copilot
custom:minimax_m3
```

3. In `provider-model-catalog.json`, remove every provider record whose key/value blob contains:

```text
minimax
copilot
githubcopilot
```

4. If cache cleanup alone does not stick, patch the installed server bundle with two filters:

- after the built-in provider array, filter `PI` to remove `minimax`, `minimax-cn`, and `copilot`;
- in the final provider injection function, block provider keys and base URLs containing `githubcopilot.com` or `api.minimax`.

Prefer a tiny surgical replacement around known minified anchors such as:

```text
}];function p9(){let I={};for(let l of PI)
```

and

```text
n.push({provider:p,label:V,base_url:F,models:w,available_models:w
```

Do not bulk-delete the minified provider list; raw strings may remain in the bundle, but the serving path must be filtered.

5. Restart under launchd and clear stale PIDs if the old process still owns port 8648:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.webui
sleep 3
lsof -nP -i :8648
pgrep -fl 'hermes-web-ui|hermes_bridge.py|dist/server/index.js'

# If old PID still owns 8648:
pkill -f '/Users/appleoppa/.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js' || true
pkill -f '/Users/appleoppa/.npm-global/lib/node_modules/hermes-web-ui/dist/server/agent-bridge/hermes_bridge.py' || true
sleep 2
launchctl kickstart -k gui/$(id -u)/ai.hermes.webui
```

## Verification

Pass only when all are true:

- `modelVisibility` no longer contains the banned provider;
- `hiddenProviders` and `disabledProviders` contain the banned provider names;
- provider catalog cache has no banned keys;
- server bundle contains the explicit built-in and runtime filters;
- port 8648 is owned by the new expected Web UI process;
- recent post-restart `server.log` has no new `api.githubcopilot.com`, `api.minimax`, or `Provider: minimax` hits.

HTTP API probes may return 401 due Web UI auth; do not treat 401 as failure for this repair. The useful checks are file readback, process ownership, port ownership, and post-restart log absence.

## Boundary

Do not remove a provider from Hermes core `~/.hermes/config.yaml` unless the user explicitly asks. Web UI catalog hard-banning can coexist with core provider retention for CLI or background multi-LLM scripts.
