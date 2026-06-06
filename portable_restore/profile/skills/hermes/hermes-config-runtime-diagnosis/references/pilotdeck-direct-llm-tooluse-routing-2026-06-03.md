# PilotDeck direct LLM tool-use routing runbook (2026-06-03)

## Trigger

Use when an adjacent local agent UI/runtime such as PilotDeck reports model capability errors while Hermes-side providers are otherwise healthy, especially:

```text
Model <model> does not support tools
Model <model> does not support streaming
```

## Key lesson

Do not keep debugging only the shared Hermes bridge if the failing runtime is a separate agent. Check the adjacent agent's own model catalog, router tiers, fallback list, API protocol, and startup env loading.

In this session, PilotDeck was physically isolated under `~/.pilotdeck-agi` and used `~/.agent-bridge` only as a bridge. The durable fix was to make PilotDeck's agent/tool-use path use a direct OpenAI-compatible provider that actually supports tools, while keeping no-tools models out of token-saver tiers that can receive agent tool payloads.

## Diagnosis pattern

1. Inspect the adjacent agent config, not just Hermes config.
   - Example path: `~/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`.
2. Inspect router events / chat logs for the selected provider/model and protocol.
   - Example signals:
     - `decision agnes_ai agnes-2.0-flash simple tokenSaver`
     - `error ... Model agnes-2.0-flash does not support tools`
3. Compare selected route against declared capabilities.
   - If `supportsToolUse: false`, the model must not be selected for an agent request that includes tools.
4. Verify whether the runtime provider implementation supports the required upstream API shape.
   - PilotDeck's OpenAI provider used `/chat/completions`; GPT/Claude providers that require Responses API should not be called “direct” unless the runtime has a Responses adapter.
5. Prefer a real direct provider with matching capability over pretending all bridge models support all features.

## Fix pattern

1. Back up the adjacent agent config.
2. Store direct provider credentials in the adjacent agent's own hidden env file (not in YAML), e.g. `~/.pilotdeck-agi/home/.pilotdeck/.env`, `chmod 600`.
3. Patch startup scripts so the adjacent agent and its UI server source that env file before loading config.
4. Set the agent default model and all tool-capable router tiers/fallbacks to a provider/model that actually supports tools.
5. Keep no-tools models either out of those tiers or explicitly limited to no-tools use.
6. Restart gateway/UI processes and verify API endpoints and browser UI.

## Verification checklist

- Config readback shows the intended agent model and direct provider URL.
- Direct API smoke with a `tools` payload succeeds and returns at least one tool call.
- The adjacent agent's own model runtime smoke succeeds with a `tool_call_end`/equivalent event and no error.
- Browser/UI smoke returns a normal assistant message.
- Latest router event selects the tool-capable provider, not the no-tools model.
- Chat log has `turn_result success completed`, not `model_error`.

## Boundary

Do not force GPT/Claude into `/chat/completions` if their configured upstream path is Responses API. If the adjacent runtime only supports chat completions, use a compatible direct provider for now, or implement a Responses adapter as a separate code change.
