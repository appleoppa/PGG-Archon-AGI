# PilotDeck channel reconnect + evidence-chain verification (2026-06-03)

## When to use

Use when the user asks to reopen/restore PilotDeck's channel and continue Hermes↔PilotDeck synchronized evolution.

## Durable pattern

PilotDeck has multiple layers that must be verified separately:

1. **Bridge/model adapter** — local GPT bridge on `127.0.0.1:18888` if configured.
2. **PilotDeck gateway** — standalone `pilotdeck server`, typically `127.0.0.1:18789`.
3. **UI server** — Express API, typically `127.0.0.1:3001`.
4. **Vite client** — frontend, typically `127.0.0.1:5173`.
5. **Evidence chain** — `~/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evidence_chain*.{py,json,md,jsonl}`.

Do not claim the channel is restored from port checks alone. Run at least one real gateway turn and confirm `turn_completed` with no `error` events.

## Startup sequence

Start the existing wrappers, not ad-hoc commands, so `PILOT_HOME`, `PILOTDECK_CONFIG_PATH`, and hidden `.env` are sourced:

```bash
~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_llm_bridge.sh
~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_second_agi.sh
~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_ui.sh server
~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_ui.sh client
```

Run them as tracked background processes, then verify listeners on `18888/18789/3001/5173`.

## Common repair: Node native module ABI drift

If the UI server fails with `ERR_DLOPEN_FAILED` and a `better-sqlite3` `NODE_MODULE_VERSION` mismatch after a Node/runtime change, rebuild the native module in the PilotDeck repo:

```bash
cd ~/.pilotdeck-agi/PilotDeck
npm rebuild better-sqlite3
npm run build
```

Then restart the UI server and re-check `/health` plus `/api/config`.

## Config and onboarding readback

Verify the UI server reads the intended hidden deployment:

```text
GET http://127.0.0.1:3001/api/config
GET http://127.0.0.1:3001/api/projects
POST http://127.0.0.1:3001/api/config/validate  # with raw YAML body
```

Expected signals:

- `path` is `~/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`
- `validation.valid == true`
- `agent.model` points to the tool-capable main model
- project path is under the hidden home
- no `_placeholder` provider remains on the live entrypoint

`/api/config/validate` is POST-only in this runtime; a GET can redirect/404 and should not be treated as failure.

## Real gateway smoke

Use `createRemoteGateway()` from the PilotDeck repo, read the `server-token`, submit one turn, and summarize event types/text/errors. Ensure the client/process is closed or externally bounded; otherwise the successful turn may finish but the Node process can stay alive on the WebSocket and hit the terminal timeout.

Evidence to report:

```text
sessionKey: web:s_...
runId: ...
eventTypes include: turn_started, context_budget, assistant_text_delta, turn_completed
completed: true
errors: []
text contains an expected marker such as SYNC_CHANNEL_OK
```

If the smoke command times out only after `completed=true` and `errors=[]`, report that the turn succeeded but the probe needs explicit WebSocket teardown; do not treat it as model/channel failure.

## Continue synchronized evolution

If evidence-chain wrappers already exist, run the additive wrapper rather than inventing a new pipeline:

```bash
cd ~/.pilotdeck-agi/home/.pilotdeck/reports
python3 pilotdeck_evidence_chain_round8.py
```

Read back:

- JSON report verdict
- Markdown report summary
- JSONL evidence-chain line count increased
- invariant checks count
- pipeline status
- EVM score / beta_bg
- model boundary unchanged unless intentionally changed

Finally update Hermes `~/.hermes/data/EVOLUTION_MANIFEST.json` with a compact summary and read it back.
