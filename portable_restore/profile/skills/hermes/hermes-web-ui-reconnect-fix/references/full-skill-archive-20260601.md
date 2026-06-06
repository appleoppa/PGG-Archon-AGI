---
name: hermes-web-ui-reconnect-fix
description: Diagnose and repair Hermes Web UI dialog disconnects caused by local hermes-agent runtime bootstrap failures, especially missing pip in the bundled venv.
version: 1.4.0
author: Hermes Agent
tags: [hermes, web-ui, reconnect, bootstrap, venv, pip, gateway, bridge, profile-autostart]
---

# Hermes Web UI Reconnect Fix

Use this when Hermes Web UI chats stop responding, sessions seem disconnected, or one profile works while another does not, and logs show bootstrap or editable-install failures.

## Common root cause

Frequent local causes include:
- `~/.hermes/hermes-agent/venv/bin/python: No module named pip`
- Desktop boot loops that keep trying to install Hermes in editable mode
- Bridge or gateway processes stuck in restart cycles
- **macOS `/var/folders/` cleanup of the bridge worker socket directory** (Variant A) and **missing `/tmp/hermes-agent-bridge-workers/` directory** (Variant B) — see Pitfalls
- **Web UI startup hanging before listening because profile gateway autostart iterates through many profiles whose gateways do not report `running` quickly**. In this state a node process may exist, but `lsof -iTCP:8648 -sTCP:LISTEN` is empty and browser websocket errors appear. See `references/profile-gateway-autostart-hang.md`.

## Diagnosis

1. Check live processes.
   - `hermes-web-ui` node server
   - `hermes_bridge.py` — **count them**: `ps aux | grep hermes_bridge | grep -v grep | wc -l`. If >2, bridges accumulated from partial restarts. 1 main bridge + occasional worker is normal; 4+ is stale accumulation and likely the root cause of empty worker directories.
   - `hermes_cli.main gateway run`

2. Inspect Hermes logs for:
   - `No module named pip`
   - `Desktop boot failed`
   - editable install complaints such as missing `setup.py` / `setup.cfg`
   - repeated bridge restart messages
   - `connect ENOENT .../hermes-agent-bridge-workers/...sock` (Variant A — `/var/folders/` path)
   - `Errno 2: No such file or directory` with `[chat-run-socket] fixed context estimate failed` (Variant B — `/tmp/` path)

3. Verify the venv state.
   - Check that `~/.hermes/hermes-agent/venv/bin/python` exists
   - Check whether `~/.hermes/hermes-agent/venv/bin/pip` exists
   - If `pip` is missing but `python -m pip --version` and `pip3` work, create a low-risk shim: `ln -sf pip3 ~/.hermes/hermes-agent/venv/bin/pip`

4. Before repair, preserve profile gateways that may be serving active Web UI chats.
   - Do not assume a gateway is residual just because it has no messaging platforms.
   - Prefer restarting only Web UI node + bridge when the error is a missing bridge socket.
   - Keep active `hermes_cli.main ... gateway run` processes unless logs show the gateway itself is broken.

5. Distinguish "node process exists" from "Web UI is actually serving".
   - Check `lsof -nP -iTCP:8648 -sTCP:LISTEN`; a node process without a listening socket means startup has not completed.
   - Check `curl -sS -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8648/`.
   - Check `/tmp/hermes-agent-bridge.sock`; absence after startup usually means the bridge did not reach ready state.
   - **Key: read the right log file.** There are TWO log files:
     - `~/.hermes-web-ui/server.log` — stdout/stderr capture (brief startup banner + SQLite warnings)
     - `~/.hermes-web-ui/logs/server.log` — JSON pino-format detailed bootstrap log **(PRIMARY diagnostic source)**
     Always check `logs/server.log` for the real bootstrap state. The plain `server.log` is just a process output capture.
     Use `grep "<PID>" ~/.hermes-web-ui/logs/server.log | grep -E 'listening|bootstrap|gateway-autostart|Server:'` to find the relevant PID's entries.
   - If `logs/server.log` shows repeated `[gateway-autostart] ... did not report running within timeout` lines, the process is NOT hung — it is iterating through profiles one by one, each taking ~16 seconds. With N profiles, total boot time is N × 16s. Continue waiting or use a workaround (see Repair step 5).
   - **Bootstrap PID vs actual server PID**: The process you see in `hermes-web-ui start` output (PID from `ps`) can be a short-lived bootstrap process. Once profile gateway autostart completes, the actual listening server may be a **different PID** (lower or higher). When tracking logs, grep by BOTH PIDs to see the full story: `grep -E '<PID1>|<PID2>' ~/.hermes-web-ui/logs/server.log`. The listening server is the one that emits `[agent-bridge] ready` and `Server: http://localhost:8648`.
   - **Check Web UI version:** `grep 'hermes-web-ui v' ~/.hermes-web-ui/server.log | tail -1`. Versions matter for available workarounds.

6. If recent Web UI dialog boxes are missing after profile/model cleanup or profile renames, compare the live DB with recent DB backups before assuming deletion.
   - First identify the actual runtime DB, not just the expected legacy path. Use `lsof -nP | grep 'hermes-web-ui.db'` against the running node process; some launches use `~/packages/server/data/hermes-web-ui.db` while older checks may look at `~/.hermes-web-ui/hermes-web-ui.db`.
   - Inspect the actual runtime DB: `PRAGMA integrity_check`, `sessions` grouped by profile/source, and recent `last_active` rows.
   - Query the authenticated session list API after DB changes, because “DB row exists” is not the same as “UI can see it”: read `~/.hermes-web-ui/.token` locally without printing it and call `/api/hermes/sessions?limit=20` with `Authorization: Bearer <token>`.
   - Compare against recent backups under `~/.hermes/workspace/存档/` by copying backup DBs to a temporary ASCII-safe path first if SQLite has trouble opening paths containing Chinese characters.
   - If backup contains sessions missing from live DB, restore by `INSERT OR IGNORE` for missing `sessions`, `messages`, `session_usage`, and related harmless metadata into the actual runtime DB only; do not replace the whole DB unless explicitly authorized, because the live DB may contain newer chats.
   - Always copy the current live DB to a timestamped backup before any merge.
   - After merge, verify `PRAGMA integrity_check`, session counts, visible session IDs/titles through the API, bridge socket existence, and HTTP 200 from `http://127.0.0.1:8648/`.
   - Profile filters matter: the general sessions endpoint filters to known/current profiles. If restored sessions have a retired profile name (for example a renamed profile), either query with that profile explicitly or remap only the affected recovered session rows to the current replacement profile after taking a backup.
   - See `references/runtime-db-vs-legacy-db.md` for the concrete recovery pattern and API probes.

## Repair

1. Restore pip inside the hermes-agent venv.
   - Run `python -m ensurepip --upgrade` with the venv interpreter when pip module is absent.
   - Confirm `python -m pip --version` works.
   - If only the `pip` executable path is missing while `pip3` exists, create the shim: `ln -sf pip3 ~/.hermes/hermes-agent/venv/bin/pip`.

2. If logs show `connect ENOENT .../hermes-agent-bridge-workers/...sock` or `Errno 2: No such file or directory`, identify the variant first.

   **Variant A — `/var/folders/.../T/` path**: macOS periodically purges temp directories. Bootstrap auto-recreates the directory when the bridge restarts. Check if the directory has been recreated: `ls -la /var/folders/.../T/hermes-agent-bridge-workers/` with the actual hash from the ENOENT message. If the directory exists and is non-empty, the ENOENT was a transient macOS cleanup event — no manual action needed.

   **Variant B — `/tmp/hermes-agent-bridge-workers/` missing**: Create it manually (`mkdir -p /tmp/hermes-agent-bridge-workers`), then restart Web UI node + bridge only. Verify the directory is populated with worker sockets during chat.

   **Both variants**: Do NOT `rm -rf` either worker directory manually — bootstrap recreates it automatically on restart. Stop `hermes-web-ui/dist/server/index.js` and `hermes_bridge.py`, remove stale bridge sockets such as `/tmp/hermes-agent-bridge.sock`, then start Web UI node server again. Avoid killing profile gateways unless separately proven broken.

3. For full local UI stack restart only when needed.
   - Stop the Web UI node server.
   - Stop bridge processes.
   - Stop gateway processes only if they are stuck or belong to the broken scope.
   - Restart the Web UI so it recreates the bridge/gateway handshake.

4. Recheck that the chats reconnect.

5. If Web UI startup is blocked by profile gateway autostart timeouts, use a scoped startup bypass.
   - Confirm evidence first: node exists but 8648 is not listening, `/tmp/hermes-agent-bridge.sock` is missing, and `logs/server.log` repeats `[gateway-autostart] ... did not report running within timeout` for nonessential profiles.
   - **Check Web UI version first.** Run `grep 'hermes-web-ui v' ~/.hermes-web-ui/server.log | tail -1`.
   - **v0.5.x** (older): A proven local patch is to guard the `await n4()` startup call with `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1`, then start Web UI with that environment variable.
   - **v0.6.x/v0.6.5**: Some builds do not include `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART` in the compiled JS (`grep -c` returns 0). The server unconditionally iterates all configured profiles. Workarounds:
     a. **Wait it out** — each profile takes ~16s timeout; with N profiles, total boot time ≈ N × 16s. The `hermes-web-ui` CLI health check gives up at 30s, but the node process continues in the background. Eventually `logs/server.log` shows `Server: http://localhost:8648`.
     b. **Pre-start gateways** — before launching Web UI, start gateways for all profiles: `hermes profile list` → `hermes gateway start --profile <name>` for each. If they're already running (`running` status), Web UI skips them instantly.
     c. **Patch the server code** — backup `~/.npm-global/lib/node_modules/hermes-web-ui/dist/server/index.js`, then add a `process.env.HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART === "1"` early return at the start of the minified `async function Wk(){...}` gateway-autostart loop. Start with `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1 hermes-web-ui start 8648`. Verify log contains `[gateway-autostart] skipped by HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1`, one node process, one bridge process, HTTP 200.
     d. **Reduce profile count** — fewer profiles = shorter boot time. Consider removing unused profiles or only keeping active department profiles.
   - Restart only Web UI node + bridge. Keep known active/default/profile gateways running unless separately proven broken.
   - After successful startup, optionally terminate stale bridge processes from previous failed starts, but do not stop active gateways merely because they have no messaging platforms.
   - This is a startup sequencing workaround; do not change provider credentials or model config unless provider logs independently show an auth/model failure.

6. Do not confuse the Hermes dashboard with Hermes Web UI.
   - `hermes dashboard --stop/start` controls the separate dashboard service, not necessarily the npm-installed `hermes-web-ui` server on port 8648.
   - For Web UI on port 8648, use `hermes-web-ui status`, `hermes-web-ui stop`, `hermes-web-ui restart 8648`, and verify with `lsof -nP -iTCP:8648 -sTCP:LISTEN` plus `curl http://127.0.0.1:8648/`.
   - If an attempted restart reports `health check failed after 30s`, inspect `~/.hermes-web-ui/logs/server.log` (the JSON bootstrap log, not the stdout capture). If it shows profile autostart timeouts but no listener/socket:
     - **Wait**: the server is still iterating through profiles (v0.6.0 has no skip flag). Each takes ~16s. Server eventually starts after N × 16s.
     - **Or pre-start gateways** before launching Web UI.
     - Do not edit model/provider config — the startup timeout is a sequencing issue, not a config issue.

## Verification

- `python -m pip --version` succeeds in the hermes-agent venv
- `~/.hermes/hermes-agent/venv/bin/pip` exists or symlinks to `pip3`
- Web UI node server is running and listening on the expected port, commonly `8648`
- `/tmp/hermes-agent-bridge.sock` exists after restart
- server log shows `[agent-bridge] ready` and `Server: http://localhost:8648`
- `curl http://127.0.0.1:8648/` returns HTTP 200
- Auth-protected API routes may return 401 from curl; that alone does not mean Web UI is down
- affected chats respond normally

### Fast repair for missing main bridge socket while Web UI still listens

If the user reports `Error: connect ENOENT /tmp/hermes-agent-bridge.sock` and checks show Web UI still returns HTTP 200 on port 8648 but `/tmp/hermes-agent-bridge.sock` is absent, treat it as a local bridge bootstrap/socket failure, not a provider/model issue.

Recommended scoped repair:
1. Record evidence first: `hermes-web-ui status`, `lsof -nP -iTCP:8648 -sTCP:LISTEN`, `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8648/`, `ls -la /tmp/hermes-agent-bridge.sock /tmp/hermes-agent-bridge-workers`, and node/`hermes_bridge.py` process list.
2. Stop duplicate launchd-managed Web UI if it is racing a manually-started server: `launchctl list | grep ai.hermes.webui`, then `launchctl bootout gui/$(id -u)/ai.hermes.webui` if needed. This does not delete the plist; it only removes the duplicate service from the current launchd domain.
3. Stop Web UI and stale bridges: `hermes-web-ui stop`, then kill remaining `hermes-web-ui/dist/server/index.js` and `hermes_bridge.py` processes if still present.
4. Remove only stale main socket and PID state: `rm -f /tmp/hermes-agent-bridge.sock ~/.hermes-web-ui/server.pid`; ensure worker dir exists with `mkdir -p /tmp/hermes-agent-bridge-workers`. Do not `rm -rf` worker directories.
5. If the installed server supports the skip flag (`grep -c HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART .../dist/server/index.js` > 0), restart with `HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1 hermes-web-ui start 8648` to avoid slow multi-profile gateway autostart loops. Otherwise wait out profile iteration or pre-start gateways.
6. Verify `/tmp/hermes-agent-bridge.sock` exists, `curl` returns 200, one node server listens on 8648, and logs show `[gateway-autostart] skipped by HERMES_WEB_UI_SKIP_PROFILE_GATEWAY_AUTOSTART=1`, `[agent-bridge] ready at ipc:///tmp/hermes-agent-bridge.sock`, and `Server: http://localhost:8648`.

## Notes

- This is a local runtime/bootstrap issue, not necessarily a model/provider problem.
- Do not jump straight to provider config edits if the logs already show missing `pip` or editable-install failures.
- If multiple profiles are involved, repair the shared runtime first, then recheck profile-specific gateways.

## Node process exists but port not listening — additional failure modes

Beyond the profile-gateway-autostart hang, the node process can be running without listening for two distinct reasons:

1. **Still in profile iteration** (v0.6.x): The node process exists, iterating through profiles. Check `logs/server.log` for `[gateway-autostart]` entries. If present, wait or pre-start gateways.

2. **Node process crashed and relaunched silently**: After a `launchctl restart`, `ps` shows a new node PID but `netstat` shows no listener on 8648, and the old PID is gone. `logs/server.log` shows `[bootstrap] listening on 0.0.0.0:8648` followed by a long sequence of gateway-autostart iterations, but no subsequent `Server: http://localhost:8648` entry before the process disappears. The node process was killed by launchd (possibly a timeout or crash) and a new one started. The new process restarts the same bootstrap sequence. **Fix**: Check `launchctl error` for the service, verify the launchd plist is not timing out, and use `launchctl kickstart -kp gui/$(id -u)/com.appleoppa.hermes-web-ui` to force a clean restart rather than relying on auto-restart cycles.

### Login rate limiter during diagnosis/testing (P2)

**Root cause**: The Web UI has a built-in in-memory rate limiter that locks IP addresses after 3 failed password login attempts (`K_=3`). Lock duration is 15 minutes (`S_=15*60*1000`). There is also a global lock (50 failures → 30 min). The lock is keyed by request IP address.

**Evidence**: `{"error":"Too many login attempts, please try again later"}` returned from `POST /api/auth/login` with correct `admin`/`123456` credentials.

**What happens**: Testing login via curl or the browser raises the failure counter. Once hit, all logins from that IP are blocked for 15 minutes — even valid credentials. The rate limiter is in-memory only (not persisted to disk), so **restarting the Web UI server clears it**.

**Default credentials** (when `users` table is empty — first login auto-creates admin):
   - Username: `admin`
   - Password: `123456`

**Wrong response**: Telling the user to wait 15 minutes when the dev needs to continue testing. Also wrong: assuming credentials are wrong when the rate limiter is actually the blocker.

**Correct response**: Restart the Web UI server (`hermes-web-ui stop; hermes-web-ui start 8648`) to clear the in-memory rate limiter. Or use `AUTH_DISABLED=1` as a startup env var (see below).

### `AUTH_DISABLED=1` during diagnosis (P3)

**When to use**: When the login rate limiter is triggered and you need the API accessible immediately for testing / repair work. Also useful when diagnosing server-side issues without the auth layer adding noise.

**How**: `AUTH_DISABLED=1 hermes-web-ui start 8648`. This causes the auth middleware to return null tokens (auth disabled), making all API routes accessible without authentication. Note: the rate limiter on the login endpoint is independent of AUTH — restarting the server also clears the rate limiter.

**Limitation**: The SPA (Vue.js frontend served at `/`) still shows a login page; but API calls from tools (curl, scripts) work without tokens. The browser's SPA may still display a login form. For full bypass, clear browser localStorage/tokens and open an incognito window.

### `hermes-web-ui stop` does not always kill the process (P2)

**Root cause**: The `hermes-web-ui stop` CLI sends SIGTERM to the node process. If the node process is in a blocking state (e.g., mid-gateway-autostart loop), SIGTERM may not be processed before the CLI returns, and the server.pid file may persist. A subsequent `hermes-web-ui start` then fails with `hermes-web-ui is already running (PID: ...)`.

**Evidence**: `hermes-web-ui stop` returns "✓ stopped" but `ps -p <PID>` shows the process still alive. Or `hermes-web-ui start` says "already running".

**Correct response**: Kill directly with `kill <PID>`, check with `ps -p <PID>`. If still alive after 2s, the node process is stuck in a blocking state (gateway-autostart loop, I/O wait) and SIGTERM is not enough — use `kill -9 <PID>`. Remove stale PID file: `rm -f ~/.hermes-web-ui/server.pid`. Then start fresh.

### Bridge worker socket ENOENT — two variants (P1 on macOS)

**Root cause**: The bridge uses a worker socket directory. Two different cleanup paths can delete it:

**Variant A — macOS `/var/folders/` periodic purge**:
The worker socket directory path is `/var/folders/.../T/hermes-agent-bridge-workers/`. macOS periodically purges these temp directories, deleting the worker directory and causing `connect ENOENT` for in-flight bridge requests.

Evidence: `connect ENOENT /var/folders/8h/.../T/hermes-agent-bridge-workers/<uuid>.sock` in bridge.log, but `/tmp/hermes-agent-bridge.sock` (main socket) still exists.

**Variant B — `/tmp/` worker directory missing or empty**:
The bridge also uses `/tmp/hermes-agent-bridge-workers/` for worker sockets. If this directory does not exist at startup — OR if it exists but is EMPTY because stale bridge processes accumulated from prior restarts ate the socket claims — `context_estimate` calls fail with `Errno 2: No such file or directory` even though the main bridge socket is alive.

Evidence: `Errno 2: No such file or directory` in Web UI chat responses, bridge.log shows `[agent-bridge-client] request rejected`, `[chat-run-socket] fixed context estimate failed`, and `ls /tmp/hermes-agent-bridge-workers/` returns empty (directory missing, present-but-empty, or absent). A fallback `final local context estimate` is used, so chat still works but the error appears to the user.

**Key diagnostic sign — stale bridge accumulation**: When `ps aux | grep hermes_bridge | grep -v grep | wc -l` returns 3+ processes and both `/tmp/hermes-agent-bridge-workers/` and `/var/folders/.../T/hermes-agent-bridge-workers/` are present but empty or nearly empty, the root cause is likely stale bridges from partial restarts, not a macOS temp purge. Each restart spawns a new bridge but leaves old ones as zombies — they hold the socket but cannot serve new worker requests.

**Self-heal**: Bootstrap auto-recreates both directories when the node server restarts. The ENOENT is a brief disruption if the node process survived.

**Wrong responses**:
- `rm -rf /var/folders/.../T/hermes-agent-bridge-workers/` or `/tmp/hermes-agent-bridge-workers/` as a repair step — unnecessary and adds risk.
- Treating this as a provider/model failure — it is a local socket path issue.
- Stopping profile gateways when only the bridge worker directory is missing.

**Correct response for Variant A**: Check if directory was recreated (`ls -la` with the hash from the error log). If node is still up and directory exists, observe and confirm recovery. Only restart node+bridge if the ENOENT is persistent.

**Correct response for Variant B**: First, kill ALL stale bridge processes (`ps aux | grep hermes_bridge | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null`), confirm dead, clean old sockets (`rm -f /tmp/hermes-agent-bridge.sock`), create the directory if absent (`mkdir -p /tmp/hermes-agent-bridge-workers`), then restart Web UI node + bridge. Verify with `ls /tmp/hermes-agent-bridge-workers/` — empty at rest is normal (sockets appear during active chat context estimates). Use `scripts/bridge_enoent_diagnosis.sh` for automated multi-step diagnosis. See `references/stale-bridge-accumulation-2026-05-29.md` for a real-world case with 5 stale bridges.
