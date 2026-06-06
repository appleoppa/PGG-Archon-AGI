# Profile gateway autostart hang during Web UI startup

Use when Hermes Web UI reports websocket errors and a node process exists, but the server never reaches `Server: http://localhost:8648`.

## Symptom pattern

- `ps` shows `hermes-web-ui/dist/server/index.js` running.
- `lsof -nP -iTCP:8648 -sTCP:LISTEN` is empty.
- `curl http://127.0.0.1:8648/` fails to connect.
- `/tmp/hermes-agent-bridge.sock` is missing.
- `~/.hermes-web-ui/logs/server.log` repeats lines like:
  - `[gateway-autostart] gateway started via Hermes CLI service profile=...`
  - `[gateway-autostart] gateway start completed but did not report running within timeout profile=...`
- Logs have not yet reached:
  - `[agent-bridge] ready`
  - `Server: http://localhost:8648`

## Diagnosis

This means the Web UI bootstrap is blocked before listening. The browser surfaces it as a websocket error, but the immediate issue is startup sequencing: Web UI is trying to auto-check/start every profile gateway before it opens the HTTP/WebSocket server.

**Critical: read the right log file.** The detailed bootstrap logs are in `~/.hermes-web-ui/logs/server.log` (JSON pino format), NOT `~/.hermes-web-ui/server.log` (which is just stdout/stderr capture). Always check `logs/server.log` first.

The process is NOT truly hung — it is iterating through profiles one by one. With N profiles, each taking ~16 seconds, total boot time ≈ N × 16s. The `hermes-web-ui` CLI health check gives up at 30s but the node process continues.

Do not treat this as a provider outage merely because a chat uses a custom model. First prove the server has reached listen state.

## Repair pattern

1. Preserve active gateways.
   - Do not stop default or known active profile gateways unless logs prove the gateway itself is broken.
   - Do not assume a profile gateway is residual because it has no messaging platforms.

2. Stop only failed Web UI node/wrapper processes and old bridge processes from failed starts.

3. Start Web UI, accounting for version differences.

   **v0.5.x** (older): The env var `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1` may work to bypass profile gateway autostart. If so, use:

   ```bash
   env -u HERMES_AGENT_BRIDGE_BROKER_PID \
     -u HERMES_AGENT_BRIDGE_WORKER_PROFILE \
     -u HERMES_AGENT_BRIDGE_ENDPOINT \
     -u HERMES_AGENT_BRIDGE_BASE_HOME \
     -u HERMES_SESSION_ID \
     NODE_ENV=production PORT=8648 \
     HERMES_HOME=/Users/appleoppa/.hermes HOME=/Users/appleoppa \
     HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1 \
     /usr/local/bin/node /Users/appleoppa/.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js
   ```

   **v0.6.x** (current): The `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART` env var DOES NOT EXIST in the compiled JS. The server unconditionally iterates ALL profiles. Three workarounds:

   a. **Wait it out** — each profile takes ~16s timeout. With N profiles, boot time ≈ N × 16s. The CLI reports "health check failed" at 30s but the node process continues in the background. Check `logs/server.log` for progress.

   b. **Pre-start gateways** — before launching Web UI, run `hermes gateway start --profile <name>` for each profile. Web UI skips already-running profiles instantly.

   c. **Patch the compiled JS** — add a `process.env.SKIP_AUTOSTART` check in the gateway autostart code section of `dist/server/index.js`.

4. Verify:
   - `lsof -nP -iTCP:8648 -sTCP:LISTEN`
   - `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8648/` returns `200`
   - `/tmp/hermes-agent-bridge.sock` exists
   - `logs/server.log` shows `[agent-bridge] ready`, and `Server: http://localhost:8648`
   - Authenticated sessions API returns HTTP 200 when called with the local token, without printing the token.

## Pitfalls

- A live node process is not enough; verify the listening port.
- Do not fix this by editing provider keys, model config, or auth files unless independent logs show those are broken.
- Do not kill all profile gateways as a shortcut; active Web UI chats may depend on profile gateways that have no messaging platforms.
- A local patch in `dist/server/index.js` may be overwritten by Web UI upgrades; if the issue recurs after upgrade, recheck whether the guard still exists or whether an upstream flag replaced it.
- The env var `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART` only works in v0.5.x. In v0.6.x the compiled code does not check any env var for this purpose.
- Many profiles amplify boot time: each profile adds ~16s to startup. Users with the Apple central case system (14+ PGG department profiles) will see ~3+ minute boot times.
