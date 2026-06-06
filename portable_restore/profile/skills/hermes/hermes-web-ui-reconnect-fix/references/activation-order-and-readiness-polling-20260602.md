# Component activation order and readiness polling — 2026-06-02

## When this matters

When restarting a Hermes Web UI that is managed by launchd and has multiple interdependent processes (gateway, bridge, Web UI server, plugins). The root cause of "dialog doesn't continue" is often NOT a single failure, but a race condition introduced by activating all components at once without waiting for readiness between layers.

## The failure pattern observed

1. `launchctl kickstart -k` was called → returned "✓ restarted" immediately
2. Web UI status checked instantly → "not running"
3. But 3 seconds later, port 8648 was listening, bridge was ready
4. During the gap, bridge `context_estimate` requests failed with "socket closed" because the worker was still initializing
5. This looked like a broken system, but was actually just a timing issue

## Telltale log signatures

In `bridge.log`:
```
[agent-bridge-client] request rejected   (worker closed without a response)
[agent-bridge-client] request failed     context_estimate
[chat-run-socket] fixed context estimate failed
```

In `launchd.err.log`:
```
Error: listen EADDRINUSE: address already in use 0.0.0.0:8648
FATAL: Failed to start Hermes Web UI
```

## Corrected activation flow

```
Stop old processes
  → verify stopped
Layer 1: verify config.yaml is valid YAML, providers configured, API keys set
Layer 2: start gateway → poll until `gateway status` shows ready
Layer 3: start bridge → poll until bridge socket exists → ping → context_estimate → chat smoke
Layer 4: start Web UI → poll until port 8648 listening → HTTP 200 → WebSocket chat-run-socket ready
Layer 5: verify plugins → check entry points + config + test
```

## Polling implementation

```python
import time, socket

def wait_for_port(port=8648, timeout=10):
    """Poll until a TCP port is listening. Returns True/False."""
    for i in range(int(timeout / 0.5)):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def wait_for_bridge(sock_path='/tmp/hermes-agent-bridge.sock', timeout=10):
    """Poll until Unix socket exists. Returns True/False."""
    import os
    for i in range(int(timeout / 0.5)):
        if os.path.exists(sock_path):
            return True
        time.sleep(0.5)
    return False
```

## RTK plugin verification (correct method)

`hermes plugins list` does NOT show third-party pip-installed plugins. Verify instead:

```bash
# Check binary
rtk --version

# Check entry-point discovery
python3 -c "
import importlib.metadata
eps = importlib.metadata.entry_points(group='hermes_agent.plugins')
for ep in eps:
    print(f'{ep.name} -> {ep.value}')
"

# Check config shape (must be YAML list, not string)
python3 -c "
import yaml
with open('~/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
print(cfg.get('plugins', {}).get('enabled', []))
"
```
