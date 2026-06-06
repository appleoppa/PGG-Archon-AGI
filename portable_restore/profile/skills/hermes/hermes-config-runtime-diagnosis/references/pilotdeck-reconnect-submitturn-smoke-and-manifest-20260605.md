# PilotDeck reconnect: submitTurn smoke + evidence-chain + Hermes manifest readback (2026-06-05)

## When to use

Use this as a concrete reference for reconnecting PilotDeck with Hermes and proving the channel is usable, not merely listening on ports.

## Key durable pattern

A successful PilotDeck reconnect should prove all of the following layers:

1. `127.0.0.1:18888` bridge `/health` returns `ok` and provider list.
2. `127.0.0.1:18789` gateway `/health` returns `ok`.
3. `127.0.0.1:3001` UI server `/health` returns `ok` and `/api/config` points at `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`.
4. `127.0.0.1:5173` Vite client returns PilotDeck HTML.
5. A real `createRemoteGateway().submitTurn()` reaches `turn_completed`, `errors=[]`, and an expected text marker such as `SYNC_CHANNEL_OK`.
6. Existing evidence-chain wrapper runs successfully and appends the JSONL evidence log.
7. Hermes `~/.hermes/data/EVOLUTION_MANIFEST.json` is updated and read back.

## Node ABI drift repair

If UI server exits with `ERR_DLOPEN_FAILED` and `better-sqlite3` reports a `NODE_MODULE_VERSION` mismatch after Node upgrades, repair inside the PilotDeck repo:

```bash
cd ~/.pilotdeck-agi/PilotDeck
npm rebuild better-sqlite3
npm run build
~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_ui.sh server
```

Then re-check port `3001`, `/health`, `/api/config`, and `/api/projects`.

## submitTurn smoke shape

Prefer using PilotDeck's built artifacts and gateway token discovery rather than hand-rolled WebSocket frames:

```js
import { probeGatewayServer } from '/Users/appleoppa/.pilotdeck-agi/PilotDeck/dist/src/gateway/client/probeServer.js';
import { createRemoteGateway } from '/Users/appleoppa/.pilotdeck-agi/PilotDeck/dist/src/gateway/client/RemoteGateway.js';

const probe = await probeGatewayServer({ url: 'http://127.0.0.1:18789', timeoutMs: 5000 });
if (!probe.ok || !probe.token) throw new Error('probe_not_ok_or_missing_token');
const gw = await createRemoteGateway({ url: probe.wsUrl, token: probe.token, clientName: 'hermes-smoke' });
const sessionKey = `web:s_${crypto.randomUUID()}`;
const runId = `hermes_pilotdeck_smoke_${Date.now()}`;
let text = '';
let completed = false;
const eventTypes = [];
const errors = [];
for await (const ev of gw.submitTurn({
  sessionKey,
  channelKey: 'web',
  projectKey: 'general',
  workspaceCwd: '/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck',
  runId,
  maxTurns: 1,
  message: 'Hermes→PilotDeck 连通 smoke。请只回复：SYNC_CHANNEL_OK。不要调用工具。',
  telemetry: { ownerModule: 'manual', executionKind: 'manual', phase: 'pilotdeck_reconnect_smoke' },
})) {
  eventTypes.push(ev.type);
  if (ev.type === 'assistant_text_delta') text += ev.text;
  if (ev.type === 'turn_completed') completed = true;
  if (ev.type === 'turn_error' || ev.type === 'error') errors.push(JSON.stringify(ev));
}
console.log(JSON.stringify({ sessionKey, runId, eventTypes, completed, errors, text }, null, 2));
process.exit(completed && errors.length === 0 && text.includes('SYNC_CHANNEL_OK') ? 0 : 2);
```

Expected evidence:

```json
{
  "eventTypes": ["turn_started", "context_budget", "assistant_text_delta", "turn_completed"],
  "completed": true,
  "errors": [],
  "text": "SYNC_CHANNEL_OK"
}
```

## Evidence-chain and manifest readback

After the smoke passes, run the existing additive wrapper, if present:

```bash
cd ~/.pilotdeck-agi/home/.pilotdeck/reports
python3 pilotdeck_evidence_chain_round8.py
```

Read back at least:

- `final_verdict`
- `runtime_evidence.invariants_ok`
- `runtime_evidence.invariant_checks`
- `runtime_evidence.pipeline_ok`
- `runtime_evidence.npm_build_exit_code`
- `runtime_evidence.evm_score`
- `runtime_evidence.beta_bg`
- `evidence_log.before_lines -> after_lines`
- SHA-256 of JSON report and JSONL evidence log

Update Hermes manifest with a compact key such as `latest_pilotdeck_channel_reconnect_<date>` and read it back. Include status, layers, smoke marker, report paths, hashes, evidence log line count, and a clear boundary: channel/runtime restored and additive evidence-chain completed; no full-AGI claim and no provider-route mutation unless explicitly changed.

## Pitfalls

- Do not treat port checks alone as channel restoration.
- Do not treat `/api/config/validate` GET/404 as failure; this endpoint may be POST-only.
- Do not remove no-tools chat/auditor providers to fix tool-use routing; keep them out of agent/tool tiers instead.
- If `submitTurn` succeeds but Node stays alive on the WebSocket, make the smoke script bounded by timeout and force exit after printing evidence.
- Store one-off smoke scripts under `~/.hermes/workspace/pgg-archon-governance/`, not the home root.
