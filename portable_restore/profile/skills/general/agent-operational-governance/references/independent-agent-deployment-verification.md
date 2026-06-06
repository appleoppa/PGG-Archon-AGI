# Independent agent deployment verification

Use this reference when deploying or repairing an agent that must remain physically separate from Hermes, such as PilotDeck.

## Durable workflow

1. **Confirm isolation boundary first**
   - Keep the independent agent under its own hidden directory, e.g. `~/.pilotdeck-agi`.
   - Do not place the project under `~/.hermes/workspace` or a visible Home-root project folder.
   - If a bridge is needed, keep it as a separate hidden bridge directory, e.g. `~/.agent-bridge`, and treat bridge data as snapshots/learning suggestions rather than shared runtime state.

2. **Probe provider capabilities before routing**
   - Before making a provider the main agent/router/memory LLM, perform a direct API probe for the exact capability needed, especially `tools` / `tool_calls`.
   - Record the real response shape: HTTP status, `finish_reason`, whether `tool_calls` exists, and count.
   - Do not infer tool support from model reputation or prior provider behavior.

3. **Back up and then edit the active config**
   - Back up the live config before changing providers or router tiers.
   - If the user asks to remove a provider, remove it from both provider definitions and all router/model references; stale router references can silently route back to an unwanted model.
   - Keep non-tool providers marked `supportsToolUse: false` so they do not receive agent tool routes.

4. **Restart and verify in layers**
   - Stop stale processes on the expected ports.
   - Start gateway, server, and client from the independent agent's own directory/environment.
   - Verify with config validation endpoint first.
   - Read back provider list, agent model, memory model, router fallback, token-saver tiers, and tool-support flags from the API.
   - Run a UI smoke test and then inspect the persisted chat/turn result.
   - Inspect the latest router decision for the new session; distinguish old router event records from current routing.

5. **Report evidence, not claims**
   - Include the active config path, backup path, running ports/PIDs if relevant, validation result, API readback, UI smoke result, and current router decision.
   - If historical logs contain old-provider decisions, label them as historical rather than re-debugging already-resolved noise.

## Pitfalls

- Do not let Hermes and the independent agent share runtime directories or profile state.
- Do not use a provider as the main agent LLM until its tool-call capability is directly tested.
- Do not declare deployment complete after only editing a config; require validate + API readback + UI smoke + router evidence.
- Do not treat old router/events records as current failures without checking the latest session timestamp or latest decision entry.
