---
name: hermes-web-ui-reconnect-fix
description: Diagnose and repair Hermes Web UI dialog disconnects caused by local hermes-agent runtime bootstrap failures, especially missing pip in the bundled venv.
version: 1.5.0
author: Hermes Agent
tags: [hermes, web-ui, reconnect, bootstrap, venv, pip, gateway, bridge, profile-autostart]
---

# Hermes Web UI Reconnect Fix — Compact

## Trigger

Use when Hermes Web UI shows reconnecting, dialog disconnects, bridge socket errors, profile autostart failures, login/auth loops, or local runtime bootstrap problems.

## Fast diagnosis

1. Check whether Web UI process exists and whether its port is listening.
2. Check gateway/bridge logs for missing socket, venv/pip/bootstrap failure, profile autostart errors, or auth/rate-limit noise.
3. Confirm active profile and avoid starting duplicate gateways for the same Feishu/Lark app.
4. Distinguish UI process failure from model/provider failure.

## Env contamination & ghost socket diagnosis

When `profile worker default exited before ready` or `connect ENOENT /tmp/hermes-agent-bridge.sock` appears, suspect stale env vars or a ghost socket:

```bash
# 1. Check all HERMES_AGENT_BRIDGE_* env vars in current shell
env | grep HERMES_AGENT_BRIDGE

# 2. Check bridge broker's actual inherited env
ps eww -p <broker_pid> | tr ' ' '\n' | grep -E 'HERMES_AGENT|HERMES_BRIDGE'

# 3. Detect ghost socket: compare lsof vs filesystem
lsof -nP -p <broker_pid> 2>/dev/null | grep sock
ls -la /tmp/hermes-agent-bridge.sock
# If lsof shows the socket but ls says ENOENT → ghost socket

# 4. Test raw broker connectivity
# IMPORTANT: bridge protocol is newline-delimited JSON, NOT 4-byte length-prefixed.
python3 -c "
import socket, json, os
p = '/tmp/hermes-agent-bridge.sock'
print(f'Exists: {os.path.exists(p)}')
if os.path.exists(p):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(120)
    try:
        s.connect(p)
        req = json.dumps({'action':'ping','profile':'default'}) + '\\n'
        s.sendall(req.encode())
        data = b''
        while b'\\n' not in data:
            chunk = s.recv(65536)
            if not chunk: break
            data += chunk
        r = json.loads(data.split(b'\\n', 1)[0].decode())
        print(f'Broker ping: ok={r.get(\"ok\")}')
    except Exception as e:
        print(f'Broker fail: {e}')
    finally: s.close()
"

# 5. Check server.log bridge events matching PID of current Web UI
grep 'agent-bridge' ~/.hermes-web-ui/logs/server.log | tail -20
```

See `references/bridge-enoent-clean-restart-verification-20260606.md` for the 2026-06-06 ENOENT/EADDRINUSE clean-restart evidence pattern and the correct newline JSON bridge smoke probe.

## Common root causes

- **Multiple global `hermes-web-ui` installs / launchd cached old path**: CLI may show the upgraded version while Web UI health still reports the old version because `~/.local/bin/hermes-web-ui`, `~/.npm-global/lib/node_modules/hermes-web-ui`, an NVM global package, and `ai.hermes.webui` launchd `ProgramArguments` point to different installs. Diagnose with `hermes-web-ui --version`, `curl http://127.0.0.1:8648/health`, `lsof -iTCP:8648`, `ps -p <pid> -o command=`, package.json version checks at each global root, and `launchctl print gui/$(id -u)/ai.hermes.webui`. Repair by choosing one canonical install root, archiving duplicate old roots, replacing public bins/old roots with symlinks to canonical, then `launchctl bootout` + `bootstrap` the plist (not just `kickstart`, which can keep cached old arguments). Verify CLI version, listener command, symlink realpaths, package versions, and health `webui_version` + `webui_update_available=false`.
- bundled venv missing `pip` or broken bootstrap;
- Web UI process exists but port is not listening;
- bridge worker socket ENOENT;
- stale process not killed by `hermes-web-ui stop`;
- macOS launchd KeepAlive races with plain stop/start and leaves `EADDRINUSE` or stale bridge state;
- Node runtime drift after a user upgrades Node: launchd may use `/usr/local/bin/node` while manual `hermes-web-ui start` may use Hermes-bundled Node; confirm actual `health.node_version`, process path, and plist before declaring fixed;
- stale provider/auth/model caches can route Web UI runs to a hidden built-in provider such as `provider=minimax` at `https://api.minimax.io/anthropic`, causing 401 even when the correct custom provider `custom:minimax_m3` works;
- Web UI may keep regenerating unwanted built-in providers from the installed `hermes-web-ui/dist/server/index.js` bundle even after `config.json` hides/disables them; for repeated MiniMax/GitHub Copilot failures, hard-ban the provider at config, cache, built-in catalog, and runtime injection layers, then verify post-restart logs;
- `launchctl kickstart -k` can leave an older unmanaged Web UI PID still owning port 8648; always verify the PID that actually listens on 8648 after restart and kill stale Web UI/bridge PIDs if needed;
- `launchctl kickstart -k` returns immediately — the daemon takes 1-3 sec to bootstrap; checking readiness instantly gives a false "not running";
- plugin config shape drift, e.g. `plugins.enabled` written as the string `'[rtk-rewrite]'` instead of a YAML list, so RTK appears configured but is not enabled;
- local auth/login rate limiter interfering with diagnosis;
- profile autostart drift;
- bridge `context_estimate` request fails with "socket closed" when the bridge worker hasn't finished initializing — a hallmark symptom of activation order violation.
- **Node 版本不应回退 — 应优先适配升级**: 用户升级了 Node（如 `/usr/local/bin/node` v22/v23→v24），Web UI 报错或升级后版本漂移时，不应将 launchd plist 或手动启动路径改回 Hermes 自带旧版 Node（`~/.hermes/node/bin/node v22`）或 NVM 旧版 Node（如 `~/.nvm/versions/node/v23.11.1/bin/node`）来绕开问题。升级 Node 是用户主动行为，Web UI 提示更新 Node 意味着 v24 是新基线；回退会让用户质疑“更新有什么用”。正确做法：花时间排除真实故障（多安装位、env 污染、ghost socket、launchd cached args/循环），确保新版 Node 可正常运行。健康后，plist `ProgramArguments[0]` 应指向升级后的 Node 路径（当前用户基线常见为 `/usr/local/bin/node` v24），Web UI 包可放在用户可控单一权威位（如 `~/.hermes/webui/node_modules/hermes-web-ui`），旧 npm/nvm/global roots 只保留 symlink。验证：`health.node_version` 显示升级后的版本号，CLI/server package 均为同一版本，`webui_update_available=false`。
- **Stale env var contamination**: `HERMES_AGENT_BRIDGE_ENDPOINT`, `HERMES_AGENT_BRIDGE_BROKER_PID`, `HERMES_AGENT_BRIDGE_WORKER_PROFILE` set from a previous session/test leak into the Web UI's bridge broker. The chain: agent shell → `hermes-web-ui start` → Node.js → bridge broker (inherits all env) → profile worker (inherits broker env). The broker creates the bridge socket at the WRONG path, or the worker watchdog monitors a non-existent PID (`BROKER_PID=999999`), causing immediate exit. Detect via `env | grep HERMES_AGENT_BRIDGE` or `ps eww -p <broker_pid>`.
- **Ghost Unix socket**: The bridge broker process holds the listening socket fd (visible via `lsof`), but the filesystem entry (`/tmp/hermes-agent-bridge.sock`) was deleted. `os.path.exists()` returns False while `lsof -p <pid>` shows `fd 3u unix ... /tmp/hermes-agent-bridge.sock`. New clients get `connect ENOENT`. Often caused by a previous broker's shutdown cleanup (`sock_path.unlink()`) followed by a new broker reusing the PID's fd without recreating the filesystem entry, or by launchd restart races.
- **Worker startup timeout**: On first invocation, the profile worker imports Hermes Agent modules (29 tools, memory, skills) which can take 30-60 seconds. The upstream Web UI client may time out in 5-25s. The broker's `_wait_ready` has a 120s timeout, so the worker does eventually start — but the request fails because the client already disconnected. Retest with ≥120s timeout or wait for the worker to become cached (subsequent requests reuse the same process).

## Component activation order (critical)

Components must be activated **in order, one at a time**, with readiness verification at each step. Do NOT bundle config changes + binary patches + service restarts into a single monolithic step.

```
Layer 1: Config/Env — verify YAML, providers, API keys, plugin config shape
Layer 2: Gateway — start default profile gateway, verify it can route a model request
Layer 3: Bridge — start/verify bridge broker, ping, context_estimate (the common failure point), chat smoke
Layer 4: Web UI — start, verify port listening, HTTP 200, WebSocket ready
Layer 5: Plugins — enable in config, load, verify via entry-point discovery, test functionality
```

Each layer: **activate → verify readiness → confirm health → proceed to next layer**.

## Repair pattern

- Stop stale Web UI/gateway processes cleanly, then kill leftovers only after verifying PIDs.
- When two Node versions coexist after a user upgrade, do not leave Web UI split between `/usr/local/bin/node` and Hermes-bundled `~/.hermes/node/bin/node`. Pick the intended upgraded runtime, update launchd `ProgramArguments[0]`, and unify user-facing shims (`~/.local/bin/node/npm/npx`) to the same runtime. Prefer safe archival of the old runtime (e.g. `~/.hermes/node.v22.disabled-<timestamp>`) plus symlink compatibility over blind deletion; verify every path with `node -v`/`npm --version` and Web UI `/health` before calling it fixed.
- If a stale built-in provider route such as `provider=minimax` / `https://api.minimax.io/anthropic` reappears after cache cleanup, treat it as a session/catalog/auth residue problem: back up and surgically remove only stale built-in provider records from `auth.json`, `models_dev_cache.json`, and Web UI provider catalog cache, while preserving the correct custom provider entry such as `custom:minimax_m3` / `https://api.minimax.chat/v1`. Old session logs may still show historical 401s; distinguish pre-fix history from new post-restart failures.
- If unwanted built-in providers keep regenerating despite `hiddenProviders`/`disabledProviders`, use the hard-ban pattern: remove from `modelVisibility`, delete catalog cache entries, add explicit `dist/server/index.js` built-in/runtime filters, then restart and verify the actual PID on 8648 plus post-restart logs. See `references/webui-built-in-provider-hard-ban-20260605.md`.
- On macOS launchd-managed Web UI (`ai.hermes.webui` with KeepAlive), prefer `launchctl kickstart -k gui/$(id -u)/ai.hermes.webui`; plain PID kill/re-spawn races with launchd and can make `hermes-web-ui restart` fail or leave stale state.
- **Launchd readiness polling**: After `kickstart -k`, the daemon takes 1-3 seconds to bootstrap. Poll with 0.5s back-off up to 6 retries. Do NOT check readiness once and declare failure. Do NOT check readiness only with `hermes-web-ui status` — use `lsof -iTCP:8648` or `curl` against the port.
- If users report that direct `hermes-web-ui restart` fails under launchd, patch the CLI restart path to detect `launchctl print gui/$uid/ai.hermes.webui` and call `launchctl kickstart -k` before falling back to stop/start.
- Repair venv/bootstrap before blaming providers.
- Restart Web UI/gateway after config changes but verify each component's readiness before proceeding to the next.
- Re-test with a tiny request and log readback; do not call "fixed" from process existence alone.

### Clean-env restart (env contamination or ghost socket)

When stale `HERMES_AGENT_BRIDGE_*` env vars or ghost sockets are confirmed:

```bash
# 1. Kill ALL bridge and webui processes
pkill -9 -f 'hermes_bridge' 2>/dev/null || true
pkill -9 -f 'hermes-web-ui' 2>/dev/null || true
sleep 2

# 2. Clean stale sockets
rm -f /tmp/hermes-agent-bridge.sock
rm -rf /tmp/hermes-agent-bridge-workers 2>/dev/null || true

# 3. Unset stale env vars
unset HERMES_AGENT_BRIDGE_ENDPOINT
unset HERMES_AGENT_BRIDGE_BROKER_PID
unset HERMES_AGENT_BRIDGE_WORKER_PROFILE

# 4. Verify no stale vars remain
env | grep HERMES_AGENT_BRIDGE || echo 'clean'

# 5. Start fresh
hermes-web-ui start

# 6. Wait for broker readiness (4-6 seconds for Hermes import)
sleep 5

# 7. Verify
ls -la /tmp/hermes-agent-bridge.sock  # should exist
curl -fsS --max-time 3 http://127.0.0.1:8648/health
```

### Launchd restart loop

If launchd's `KeepAlive=true` causes constant restart cycles (EADDRINUSE in logs):

```bash
# Temporarily disable launchd job, do clean restart, then optionally re-enable
launchctl bootout gui/$(id -u)/ai.hermes.webui 2>/dev/null || true
pkill -9 -f 'hermes_bridge|hermes-web-ui' 2>/dev/null || true
sleep 2
rm -f /tmp/hermes-agent-bridge.sock
hermes-web-ui start
```

### RTK activation verification

When RTK activation is requested, verify both the binary/package and Hermes plugin state:

- `rtk --version` (binary exists);
- entry-point discoverability: `python3 -c "import importlib.metadata; eps = importlib.metadata.entry_points(group='hermes_agent.plugins'); print([ep.name for ep in eps])"`;
- `plugins.enabled` as a YAML list in config;
- **Note**: `hermes plugins list` only shows BUNDLED plugins; it does NOT show third-party pip-installed plugins like `rtk-rewrite`. Use importlib check above.

## Verification

Pass only when:

- expected port is listening;
- bridge/gateway socket exists or log confirms startup;
- Web UI can open a dialog;
- a bridge-level tiny chat smoke test returns `done: true` with expected output and no error;
- logs no longer show the triggering error, or remaining occurrences are clearly identified as pre-fix history.

## Reference

Full legacy repair notes and rare variants are archived at:

- `references/full-skill-archive-20260601.md`
- `references/launchd-restart-and-rtk-plugin-20260602.md`
- `references/webui-node24-minimax-provider-cache-20260605.md` — Node v24 Web UI runtime drift plus stale built-in MiniMax provider/cache 401 repair pattern.
- `references/webui-built-in-provider-hard-ban-20260605.md` — repeated built-in MiniMax/GitHub Copilot regeneration hard-ban pattern across config, cache, server catalog, runtime injection, restart PID ownership, and log verification.
- `references/bridge-env-ghost-socket-debug-20260605.md` — env contamination, ghost socket detection, clean-env restart procedure
