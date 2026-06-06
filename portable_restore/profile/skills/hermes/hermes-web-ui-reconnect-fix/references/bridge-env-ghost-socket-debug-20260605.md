# Bridge broker: env contamination & ghost socket debug (2026-06-05)

## Scenario

Web UI showed `profile worker default exited before ready` when opening a chat dialog. The error originated from the BridgeBroker's `WorkerProcess._wait_ready()`: the broker spawned a profile worker subprocess, but the process exited before printing `{"event":"ready"}` to stdout.

## Detection chain

```bash
# Server log showed bridge starting with wrong endpoint
grep 'agent-bridge' ~/.hermes-web-ui/logs/server.log | tail -5
# → [agent-bridge] starting: ... --endpoint ipc:///tmp/test-hermes-bridge-diagnosis.sock
#                                                ^^^^^ wrong! should be hermes-agent-bridge.sock

# Shell had stale test env vars
env | grep HERMES_AGENT_BRIDGE
# → HERMES_AGENT_BRIDGE_ENDPOINT=ipc:///tmp/test-hermes-bridge-diagnosis.sock
# → HERMES_AGENT_BRIDGE_BROKER_PID=999999
# → HERMES_AGENT_BRIDGE_WORKER_PROFILE=default

# Bridge broker's inherited env (from ps eww)
ps eww -p <broker_pid> | tr ' ' '\n' | grep -E 'HERMES_AGENT|HERMES_BRIDGE'
# → HERMES_AGENT_BRIDGE_ENDPOINT=ipc:///tmp/test-hermes-bridge-diagnosis.sock
# → HERMES_AGENT_BRIDGE_BROKER_PID=999999
```

## Ghost socket detection

```python
# Socket shows in lsof but not on filesystem
import os, subprocess
p = '/tmp/hermes-agent-bridge.sock'
print(f'os.path.exists: {os.path.exists(p)}')  # False
r = subprocess.run(['lsof','-nP','-p','<pid>'], capture_output=True, text=True)
for l in r.stdout.splitlines():
    if 'sock' in l or 'hermes' in l:
        print(l)
# → python3.1 <pid> ... 3u  unix ... /tmp/hermes-agent-bridge.sock
# File exists in kernel fd table but not on filesystem → ghost socket
```

## Root cause chain

1. Earlier session ran `hermes_bridge.py` tests that set `HERMES_AGENT_BRIDGE_ENDPOINT` to a test path
2. `hermes-web-ui start` was called from the same shell — Node.js inherited the stale env
3. Node.js passed the wrong endpoint to the bridge broker subprocess
4. Broker created/waiting-on wrong path, or workers couldn't connect back
5. Web UI's bridge client sent requests → broker worker spawn failed → `profile worker default exited before ready`

## Fix

```bash
unset HERMES_AGENT_BRIDGE_ENDPOINT
unset HERMES_AGENT_BRIDGE_BROKER_PID
unset HERMES_AGENT_BRIDGE_WORKER_PROFILE
pkill -9 -f 'hermes_bridge|hermes-web-ui' 2>/dev/null
rm -f /tmp/hermes-agent-bridge.sock
hermes-web-ui start
```

## Pitfalls

- `unset` in a shell command block inside terminal() does NOT persist to subsequent terminal() calls — each call is a new shell process. Must unset in the same command as the Web UI start.
- `env -i` strips too much — `hermes-web-ui` CLI wrapper needs PATH to find node. Use targeted `unset` instead.
- `hermes-web-ui restart` conflicts with launchd KeepAlive: the CLI's stop/start races with launchd's respawn causing EADDRINUSE. Use `launchctl bootout` then manual start for clean state.
- Stale worker test process (`--endpoint test-hermes-bridge-diagnosis.sock`) can survive `pkill -9` if it has a parent watchdog that respawns it. Check `ps aux | grep hermes_bridge` after kill.
