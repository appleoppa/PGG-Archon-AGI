# PilotDeck UI/config consistency probe

Use this reference when a local agent runtime appears fixed at the router/API layer but the UI still shows stale model/provider state.

## Durable lesson

For PilotDeck-like local agent runtimes, UI-visible model pools may be rendered from a different config segment than the live router/agent model. A route can be corrected while the UI still lists old providers if `model.providers` was not cleaned.

## Probe sequence

1. Compare raw API config from every exposed UI/API port with the on-disk YAML.
2. Inspect browser state for sticky model keys, especially keys like `pilotdeck-model` or saved provider/model selections.
3. Check both runtime routing fields and UI-rendered provider fields:
   - `agent.model`
   - router/tier/scenario model targets
   - `memory.model` if present
   - `model.providers` provider list
4. If UI still lists removed providers, rewrite/patch the provider pool rather than only changing router defaults.
5. Restart the gateway/API/UI processes that serve and cache config.
6. Verify three layers before claiming completion:
   - API config returns only expected providers/models;
   - router/agent fields point to the expected model;
   - browser UI Model Pool shows the same provider set.

## Pitfall

Do not treat `agent.model` or router target correctness as proof that the UI configuration is clean. Model Pool pages commonly render from provider declarations, not from the selected router target.

## Evidence to report

- Config file path changed and backup path if created.
- Ports/processes restarted.
- API readback provider list.
- Browser UI observation of the Model Pool or equivalent settings page.
