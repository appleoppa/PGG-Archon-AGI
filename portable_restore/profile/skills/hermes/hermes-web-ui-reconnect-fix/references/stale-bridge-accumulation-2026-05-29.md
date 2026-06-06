# Stale Bridge Accumulation — 2026-05-29

## Scenario

Web UI works but returns `Error: [Errno 2] No such file or directory` in chat responses. Chat functions but errors appear to user.

## Diagnosis findings

- Web UI node running, port 8648 listening ✓
- `/tmp/hermes-agent-bridge.sock` exists ✓
- **5 bridge processes** running (from repeated `hermes-web-ui start` without proper `stop`)
- `/tmp/hermes-agent-bridge-workers/` exists but **EMPTY** (0 socket files)
- `/var/folders/.../T/hermes-agent-bridge-workers/` exists but **EMPTY** — only 1 worker PID using `/var/folders/...` path, no sockets active

## Root cause

Multiple partial restarts each spawned a new bridge process. Old bridges stayed alive as zombies holding no-op socket claims. The worker directory was never cleaned or re-populated because the effective bridge couldn't pass worker registrations through.

## Fix sequence

1. **Kill ALL bridge processes**: `kill 3917 15822 20556 27281 27453` (5 PIDs found via `ps aux | grep hermes_bridge | grep -v grep`)
2. **Confirm all dead**: `ps aux | grep hermes_bridge`
3. **Clean old sockets**: `rm -f /tmp/hermes-agent-bridge.sock`
4. **Ensure worker directory exists** (already existed but didn't hurt to verify): `mkdir -p /tmp/hermes-agent-bridge-workers`
5. **Stop Web UI**: `hermes-web-ui stop` returned `was not running (cleaned stale PID: 945)` but node process was still alive at PID 25151
6. **Force kill node**: `kill 25151` → still alive → `kill -9 25151` → confirmed dead
7. **Clear stale PID file**: `rm -f ~/.hermes-web-ui/server.pid`
8. **Confirm port free**: `lsof -nP -iTCP:8648 -sTCP:LISTEN` → empty
9. **Start fresh**: `hermes-web-ui start 8648`
10. **Wait through profile gateway autostart**: ~3 minutes for 13 profiles (default, deepseekv4 + 11 pgg-*). The hermes-web-ui CLI health check gave up at 30s, but server continued in background.
11. **Verification**: `lsof -nP -iTCP:8648 -sTCP:LISTEN` confirmed PID 28674 listening. HTTP 200 from `curl`. Logs showed `[agent-bridge] ready` and `Socket.IO ready at /chat-run`.

## Key observations

- The `hermes-web-ui start` output PID (28822) was the bootstrap process, not the actual server (28674)
- SIGTERM (`kill`) failed on node stuck in gateway autostart loop; needed SIGKILL (`kill -9`)
- `/tmp/hermes-agent-bridge-workers/` being EMPTY at rest is **normal** — worker sockets only appear during active chat context estimates
- Profile gateway autostart sequentially visits ALL profiles, not just non-running ones. Already-running profiles are skipped instantly (~0s), but each stopped profile incurs the full ~16s timeout. With 13 profiles, total boot time ~3min.
