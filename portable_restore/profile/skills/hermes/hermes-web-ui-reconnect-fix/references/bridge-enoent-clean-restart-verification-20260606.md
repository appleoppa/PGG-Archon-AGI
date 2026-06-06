# Bridge ENOENT clean restart verification — 2026-06-06

## Class lesson

For `Error: connect ENOENT /tmp/hermes-agent-bridge.sock`, a successful fix needs both socket restoration and bridge protocol smoke testing. Do not stop at `hermes-web-ui status` or process presence.

## Observed durable pattern

Symptoms:
- Web UI PID exists and port 8648 may be listening.
- `/tmp/hermes-agent-bridge.sock` is missing.
- Logs show repeated `EADDRINUSE: address already in use 0.0.0.0:8648` from launchd restart races.
- Stale broker/worker processes may exist under both `/tmp/hermes-agent-bridge.sock` and `/var/folders/.../hermes-agent-bridge-workers/*.sock`.

Repair sequence:
1. If `ai.hermes.webui` launchd job is loaded, `launchctl bootout gui/$(id -u)/ai.hermes.webui` before killing processes. This avoids KeepAlive immediately respawning into EADDRINUSE.
2. Run `hermes-web-ui stop` if available.
3. Kill leftover `hermes_bridge.py` and `hermes-web-ui/dist/server/index.js` processes only after inspecting PIDs.
4. Remove `/tmp/hermes-agent-bridge.sock` and `/tmp/hermes-agent-bridge-workers`.
5. Re-bootstrap/kickstart `~/Library/LaunchAgents/ai.hermes.webui.plist` or use `hermes-web-ui start` if not launchd-managed.
6. Poll port 8648 and `/health`; wait a few seconds for bridge worker import before deeper smoke.

## Correct raw bridge probe protocol

The bridge does not use a 4-byte length-prefixed protocol. It expects one newline-delimited JSON request and returns one newline-delimited JSON response.

```python
import socket, json, os, time
p = '/tmp/hermes-agent-bridge.sock'
for req in [
    {'action': 'ping', 'profile': 'default'},
    {'action': 'context_estimate', 'session_id': 'smoke-bridge-enoent-fix', 'profile': 'default', 'messages': [{'role': 'user', 'content': 'ping'}]},
]:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(120)
    try:
        s.connect(p)
        s.sendall((json.dumps(req, ensure_ascii=False) + '\n').encode())
        data = b''
        while b'\n' not in data:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
        resp = json.loads(data.split(b'\n', 1)[0].decode())
        print(req['action'], resp.get('ok'), sorted(resp.keys()), resp.get('error'))
    finally:
        s.close()
```

Expected:
- `ping`: `ok=True` immediately.
- `context_estimate`: `ok=True`; may take a few seconds while the default profile worker initializes.

## Log verification

Old logs often contain historical `EADDRINUSE`/`ENOENT` from before the fix. Filter logs from the current Web UI PID's `[agent-bridge] starting` marker and only count new blocking errors after that marker.

Blocking post-restart errors to count:
- `ENOENT`
- `EADDRINUSE`
- `Fatal error during bootstrap`
- `socket closed`

Non-blocking after a manual wrong-protocol probe:
- `Broken pipe` may appear if a diagnostic client connected and closed incorrectly; rerun with newline-delimited JSON before treating it as persistent failure.
