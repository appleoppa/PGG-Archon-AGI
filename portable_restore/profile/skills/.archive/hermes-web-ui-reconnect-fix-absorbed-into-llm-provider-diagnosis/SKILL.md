---
name: hermes-web-ui-reconnect-fix
description: Diagnose and repair Hermes Web UI dialog disconnects caused by local hermes-agent runtime bootstrap failures, especially missing pip in the bundled venv.
version: 1.0.0
author: Hermes Agent
tags: [hermes, web-ui, reconnect, bootstrap, venv, pip, gateway, bridge]
---

# Hermes Web UI Reconnect Fix

Use this when Hermes Web UI chats stop responding, sessions seem disconnected, or one profile works while another does not, and logs show bootstrap or editable-install failures.

## Common root cause

A frequent local cause is:
- `~/.hermes/hermes-agent/venv/bin/python: No module named pip`
- Desktop boot loops that keep trying to install Hermes in editable mode
- Bridge or gateway processes stuck in restart cycles
- **macOS `/var/folders/` cleanup of the bridge worker socket directory** (see Pitfalls)

## Diagnosis

1. Check live processes.
   - `hermes-web-ui` node server
   - `hermes_bridge.py`
   - `hermes_cli.main gateway run`

2. Inspect Hermes logs for:
   - `No module named pip`
   - `Desktop boot failed`
   - editable install complaints such as missing `setup.py` / `setup.cfg`
   - repeated bridge restart messages
   - `connect ENOENT .../hermes-agent-bridge-workers/...sock`

3. Verify the venv state.
   - Check that `~/.hermes/hermes-agent/venv/bin/python` exists
   - Check whether `~/.hermes/hermes-agent/venv/bin/pip` exists
   - If `pip` is missing but `python -m pip --version` and `pip3` work, create a low-risk shim: `ln -sf pip3 ~/.hermes/hermes-agent/venv/bin/pip`

4. Before repair, preserve profile gateways that may be serving active Web UI chats.
   - Do not assume a gateway is residual just because it has no messaging platforms.
   - Prefer restarting only Web UI node + bridge when the error is a missing bridge socket.
   - Keep active `hermes_cli.main ... gateway run` processes unless logs show the gateway itself is broken.

5. If recent Web UI dialog boxes are missing after profile/model cleanup or profile renames, compare the live DB with recent DB backups before assuming deletion.
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

2. If logs show `connect ENOENT .../hermes-agent-bridge-workers/...sock`, diagnose before acting.
   - The worker socket directory lives under macOS `/var/folders/.../T/` — a path that macOS periodically cleans, deleting the directory and causing ENOENT.
   - **Bootstrap auto-recovers the directory** when the bridge restarts. Check if the directory has been recreated: `ls -la /var/folders/.../T/hermes-agent-bridge-workers/` with the actual hash from the ENOENT message.
   - If the directory exists and is non-empty, the ENOENT was a transient macOS cleanup event — no manual action needed.
   - If the directory is missing AND the bridge process is still running, restart Web UI node + bridge only.
   - **Do NOT `rm -rf` the worker directory manually** — bootstrap recreates it automatically on restart; manual deletion is unnecessary and adds risk.
   - Stop `hermes-web-ui/dist/server/index.js` and `hermes_bridge.py`.
   - Remove stale bridge sockets such as `/tmp/hermes-agent-bridge.sock`.
   - Start the Web UI node server again.
   - Avoid killing profile gateways unless separately proven broken.

3. For full local UI stack restart only when needed.
   - Stop the Web UI node server.
   - Stop bridge processes.
   - Stop gateway processes only if they are stuck or belong to the broken scope.
   - Restart the Web UI so it recreates the bridge/gateway handshake.

4. Recheck that the chats reconnect.

## Verification

- `python -m pip --version` succeeds in the hermes-agent venv
- `~/.hermes/hermes-agent/venv/bin/pip` exists or symlinks to `pip3`
- Web UI node server is running and listening on the expected port, commonly `8648`
- `/tmp/hermes-agent-bridge.sock` exists after restart
- server log shows `[agent-bridge] ready` and `Server: http://localhost:8648`
- `curl http://127.0.0.1:8648/` returns HTTP 200
- Auth-protected API routes may return 401 from curl; that alone does not mean Web UI is down
- affected chats respond normally

## Notes

- This is a local runtime/bootstrap issue, not necessarily a model/provider problem.
- Do not jump straight to provider config edits if the logs already show missing `pip` or editable-install failures.
- If multiple profiles are involved, repair the shared runtime first, then recheck profile-specific gateways.

## Pitfalls

### macOS `/var/folders/` worker socket directory cleanup (P1 on macOS)

**Root cause**: The bridge worker socket directory path is `/var/folders/.../T/hermes-agent-bridge-workers/`. macOS periodically purges contents of `/var/folders/` subdirectories, deleting this directory and causing `connect ENOENT` errors for in-flight requests.

**Evidence**: `connect ENOENT /var/folders/8h/dlwwrh492sx41lcnsfzqtgjm0000gn/T/hermes-agent-bridge-workers/<uuid>.sock` in bridge.log, but `/tmp/hermes-agent-bridge.sock` (main socket) still exists and Web UI is up.

**What happens**: Bootstrap auto-recreates the directory when the node server restarts. The ENOENT is a brief disruption, not a persistent failure — the system self-heals if the node is still running.

**Wrong response**: `rm -rf /var/folders/.../T/hermes-agent-bridge-workers/` as a repair step — this adds unnecessary risk and is not needed since bootstrap recreates it.

**Correct response**: Check if directory was recreated (`ls -la` with the hash from the error log). If node is still up and directory exists, observe and confirm recovery. Only restart node+bridge if the ENOENT is persistent (node itself crashed and did not restart). Use `scripts/bridge_enoent_diagnosis.sh` for automated multi-step diagnosis.
