# PilotDeck Protocol Smoke v4 — 2026-06-06

## Trigger

Use when verifying local PilotDeck link/runtime health or claiming PilotDeck is connected.

## Key lesson

Port health is not enough. A truthful PilotDeck link gate must progress from HTTP health to WebSocket protocol smoke.

## Verified local endpoints

- Gateway health: `http://127.0.0.1:18789/health`
- Web server: `http://127.0.0.1:3001/`
- Vite UI: `http://127.0.0.1:5173/`

## Smoke ladder

1. Start gateway with PilotDeck env loaded:

```bash
set -a
. /Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/.env
set +a
cd /Users/appleoppa/.pilotdeck-agi/PilotDeck
npm run server
```

Use Hermes `terminal(background=true)` for long-lived gateway; do not rely on foreground timeout or shell-level `nohup` without readback.

2. HTTP health:

```bash
curl -sS -m 5 http://127.0.0.1:18789/health
# expected: {"ok":true}
```

3. `/api/agent` auth gate without key:

```bash
curl -sS -m 5 -H 'Content-Type: application/json' \
  -d '{"projectPath":"/Users/appleoppa/.pilotdeck-agi/PilotDeck","message":"smoke","stream":false}' \
  http://127.0.0.1:3001/api/agent
# expected: {"error":"API key required"}
```

This `401` is a PASS for auth-gate presence, not an agent task success.

4. WebSocket protocol smoke:

- Connect to `ws://127.0.0.1:18789/ws`.
- First frame must be `hello`; sending request/ping first closes with `4001 hello_required`.
- `protocolVersion` must be exact string `"1.0"`, not `"1"`; otherwise closes with `4001 protocol_mismatch`.
- Use token from `~/.pilotdeck/server-token`; never print token value. Hash/metadata only.
- After `hello_ok`, call `describe_server`, then `list_projects`.

Minimal expected PASS chain:

```text
open → hello(protocolVersion="1.0") → hello_ok → describe_server response ok → list_projects response ok
```

## Common pitfalls

- Starting `npm run dev` without sourcing `.pilotdeck/.env` can fail with `MINIMAX_API_KEY is not set` and kill server/client via `concurrently`.
- Foreground `npm run server` may be killed by tool timeout; this is not PilotDeck failure. Use tracked background process.
- Running a WebSocket smoke script from an evidence directory may fail to import `ws`; use `createRequire('/Users/appleoppa/.pilotdeck-agi/PilotDeck/package.json')` or run inside repo with correct module resolution.
- `hello_required` and `protocol_mismatch` are useful verifier feedback; fix the smoke contract before declaring runtime failure.

## Boundary wording

Protocol smoke proves gateway auth handshake and basic RPC (`describe_server`, `list_projects`) over WebSocket. It does not prove full `submit_turn`, autonomous task completion, production takeover, external benchmark pass, or AGI level increase.

## Evidence pattern from verified run

- Evidence dir: `~/.hermes/workspace/pgg-archon-governance/pilotdeck-sync-next-*`
- Manifest key shape: `latest_pilotdeck_sync_evolution_<unix>`
- Rust settlement binary: `rust_modules/hermes_pgg_pilotdeck/src/bin/pilotdeck_sync_evidence.rs`
