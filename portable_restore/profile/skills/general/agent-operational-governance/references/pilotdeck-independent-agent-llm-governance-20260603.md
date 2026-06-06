# PilotDeck independent-agent LLM governance pattern (2026-06-03)

## Trigger

Use when configuring or repairing PilotDeck as an independent agent that must stay physically isolated from Hermes, especially when adding/removing LLM providers, fixing onboarding/placeholder config loops, or mixing tool-capable and no-tools models.

## Durable lessons

### 1. Verify the real startup config path, not only the edited config

PilotDeck may have multiple apparent homes. In this session the valid hidden deployment lived at:

```text
/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml
```

but opening `PilotDeck.app` read the default path:

```text
/Users/appleoppa/.pilotdeck/pilotdeck.yaml
```

which still contained placeholder onboarding config. The UI therefore asked to configure an LLM even though the hidden config was valid.

Correct pattern:

1. Query `/api/config` and read the returned `path`.
2. Query `/api/projects` and confirm project paths are under the intended hidden home.
3. If default app startup uses `~/.pilotdeck`, bridge it intentionally:

```bash
mv ~/.pilotdeck ~/.pilotdeck.placeholder-backup-<timestamp>
ln -s ~/.pilotdeck-agi/home/.pilotdeck ~/.pilotdeck
```

4. Mark onboarding complete only after config is valid and read back.

### 2. Direct capability probes before changing main LLM

Before making a model the PilotDeck main agent/router/memory model, test the exact required wire behavior:

- normal chat completion
- streaming if PilotDeck UI expects streaming
- `tools` / `tool_calls` if the model will run agent tools

Do not infer support from model reputation or a provider catalog. In this session:

- MIMO direct `/v1/chat/completions` returned a real `tool_calls` response, so it was safe as main tools model.
- Agnes was retained as chat-only with `supportsToolUse: false`.
- GPT-5.5 was usable only via a local bridge that adapts Responses API to OpenAI-style chat completions; it was added as no-tools collaboration/evolution model, not as main tools model.

### 3. Keep role boundaries explicit in config

Known-good boundary after repair:

```text
MIMO  -> main agent/router/fallback/memory/tokenSaver/tools model
GPT   -> collaboration/evolution no-tools model via local bridge
Agnes -> chat-only/no-tools standby model
```

For GPT via bridge:

```yaml
gpt55_5yuantoken:
  protocol: openai
  url: http://127.0.0.1:18888/v1
  apiKey: <LOCAL_BRIDGE_PLACEHOLDER>
  models:
    gpt-5.5:
      capabilities:
        supportsToolUse: false
        supportsStreaming: true
        supportsThinking: true
```

Keep `agent.model`, `router.scenarios.default`, `router.fallback.default`, `memory.model`, and all `tokenSaver.tiers.*.model` pointed at the tool-capable main model unless the user explicitly changes the architecture.

### 4. Add runtime assertions for chat-only models

Config-level `supportsToolUse: false` is not enough if router state, sticky routing, or explicit overrides can select a no-tools model. Add router-level protection:

- detect requests with `tools`;
- detect chat-only/no-tools providers (e.g. Agnes);
- reroute tools-bearing requests to the default tool-capable model;
- filter fallback attempts so tools requests cannot fall back to no-tools models;
- log a mutation such as:

```text
noToolsModelRerouted: { from, to, reason }
```

Verification smoke test: explicitly request `agnes_ai/agnes-2.0-flash` with a fake tool schema and assert the router decision returns MIMO and includes the mutation.

### 5. Establish drift baselines and reports

After successful config changes, write a compact baseline under the PilotDeck hidden home, e.g.:

```text
~/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_config_baseline_YYYYMMDD.json
```

Include:

- config path
- SHA-256 of `pilotdeck.yaml`
- symlink state
- provider list
- agent model
- fallback
- tokenSaver tier models
- tool-use capabilities for each provider

For Hermes-side audit trail, archive a report under:

```text
~/.agent-bridge/reports/
```

### 6. Verification gates

A PilotDeck LLM repair is not done until all pass:

1. `/api/config` path is the intended hidden config.
2. `/api/config/validate` is valid with no errors.
3. `/api/projects` paths match hidden home.
4. Ports are ready: gateway, UI server, UI client, plus local LLM bridge if configured.
5. Main model direct API probe passes for required capabilities.
6. PilotDeck `streamModel()` or UI smoke returns expected text.
7. Latest router event shows the intended provider/model.
8. Any code changes build successfully and, if in a repo, are committed with only scoped files.

## Pitfalls

- UI showing placeholder onboarding can mean the app read a different config path, not that the edited config failed.
- Removing no-tools models from the model pool may be overcorrection; keep them if useful, but exclude them from tools routes.
- GPT/Claude providers that require Responses API should not be falsely configured as direct chat-completions unless a real adapter/bridge or native provider implementation exists.
- Stale router events are historical noise; inspect the latest session decision after restart and smoke test.
