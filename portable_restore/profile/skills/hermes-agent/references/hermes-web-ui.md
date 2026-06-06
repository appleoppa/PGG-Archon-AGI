# Hermes Web UI

Hermes Web UI (`hermes-web-ui`) is a separate npm package that provides the web dashboard for Hermes Agent. It is NOT part of the core `hermes-agent` install.

**Homepage:** https://github.com/EKKOLearnAI/hermes-web-ui
**npm:** `npm install -g hermes-web-ui`

## Token / Authentication

The web UI uses a token-based auth. On first startup it auto-generates a 64-char hex token and stores it at:

```
~/.hermes-web-ui/.token
```

To find the token:
```bash
cat ~/.hermes-web-ui/.token
```

To reset (generate a new token):
```bash
rm ~/.hermes-web-ui/.token
# then restart: hermes-web-ui start
```

## Default Port

The web UI runs on **port 8648**: http://127.0.0.1:8648

## Gateway API Server (built-in, port 8642)

The core Hermes Agent also ships with a built-in API server. It runs on **port 8642** (configured in `config.yaml` under `platforms.api_server`). It is separate from the `hermes-web-ui` dashboard and uses a different auth mechanism (API key from `config.yaml`).

## Distinguishing Which Is Running

| Port | Package | Auth |
|------|---------|------|
| 8642 | hermes-agent (built-in API server) | `platforms.api_server.key` in config.yaml |
| 8648 | hermes-web-ui | token in `~/.hermes-web-ui/.token` |

Check what's listening:
```bash
lsof -i :8642 -i :8648
```

## CLI wrapper recursion: `Argument list too long`

If `hermes-web-ui restart` reports something like:

```text
.../bin/hermes-web-ui.mjs: line 23: .../bin/hermes-web-ui.mjs: Argument list too long
```

Known cause: `bin/hermes-web-ui.mjs` has been overwritten by a bash wrapper that `exec`s the same file again, creating recursive self-exec and PATH/env growth until macOS hits argument/environment limits.

Diagnosis:
```bash
file ~/.npm-global/lib/node_modules/hermes-web-ui/bin/hermes-web-ui.mjs
sed -n '1,30p' ~/.npm-global/lib/node_modules/hermes-web-ui/bin/hermes-web-ui.mjs
which hermes-web-ui
readlink ~/.local/bin/hermes-web-ui || true
```

Expected package entry should begin with:
```text
#!/usr/bin/env node
```

Minimal reversible repair for a known package version:
```bash
TMP=$(mktemp -d)
cd "$TMP"
npm pack hermes-web-ui@<version>
tar -xzf hermes-web-ui-*.tgz
mkdir -p ~/.hermes/workspace/backups/hermes-web-ui-$(date +%Y%m%d_%H%M%S)
cp ~/.npm-global/lib/node_modules/hermes-web-ui/bin/hermes-web-ui.mjs ~/.hermes/workspace/backups/hermes-web-ui-$(date +%Y%m%d_%H%M%S)/hermes-web-ui.mjs.bad
cp package/bin/hermes-web-ui.mjs ~/.npm-global/lib/node_modules/hermes-web-ui/bin/hermes-web-ui.mjs
chmod 755 ~/.npm-global/lib/node_modules/hermes-web-ui/bin/hermes-web-ui.mjs
```

If `~/.local/bin/hermes-web-ui` shadows the npm-global bin and contains the same bad wrapper, replace it with a symlink to the npm-global bin. Then verify:
```bash
hermes-web-ui --version
hermes-web-ui status
hermes-web-ui restart
curl -fsS http://127.0.0.1:8648/health
```

Pitfall: `hermes-web-ui stop/restart` sends SIGTERM to the web-ui daemon. When testing from an agent shell, run restart in a separate process group if the shell gets interrupted, e.g. Python `subprocess.run(..., start_new_session=True)`. Also check for orphaned `dist/server/index.js` and `hermes_bridge.py` processes occupying port 8648.
