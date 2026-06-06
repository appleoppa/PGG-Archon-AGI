# Web UI custom model visibility and bottom selector troubleshooting

Use when a custom provider/model works from Hermes CLI or direct API but cannot be selected or used from the Hermes Desktop/Web UI bottom model selector.

## Key distinction

CLI/API success is not enough for UI success. Verify all three layers:

1. Hermes core config contains the provider under both `providers.<name>` and `custom_providers[]`.
2. Web UI model visibility includes the exact provider/model pair in `~/.hermes-web-ui/config.json`.
3. Web UI provider catalog cache has regenerated and the running Web UI/bridge process has restarted or refreshed.

## Known pattern

A model can work here:

```bash
hermes -z 'Return exactly: OK' --provider custom:minimax_m3 -m MiniMax-M3 --cli
```

but still fail in the bottom selector if `~/.hermes-web-ui/config.json` lacks:

```json
{
  "modelVisibility": {
    "custom:minimax_m3": {
      "mode": "include",
      "models": ["MiniMax-M3"]
    }
  }
}
```

## Diagnostic commands

Check core config without printing secrets:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
cfg=yaml.safe_load((Path.home()/'.hermes/config.yaml').read_text())
print(cfg.get('model'))
print(sorted((cfg.get('providers') or {}).keys()))
print([x.get('name') for x in (cfg.get('custom_providers') or []) if isinstance(x,dict)])
PY
```

Check UI visibility and cache:

```bash
python3 - <<'PY'
from pathlib import Path
import json
for p in [Path.home()/'.hermes-web-ui/config.json', Path.home()/'.hermes-web-ui/cache/provider-model-catalog.json']:
    print('\n##', p, p.exists())
    if p.exists():
        text=p.read_text(errors='replace')
        print('contains minimax/custom model?', 'minimax' in text.lower())
PY
```

Check running UI/bridge processes:

```bash
lsof -nP -i :8648 2>/dev/null || true
pgrep -fl 'hermes-web-ui|hermes_bridge.py|dist/server/index.js' || true
launchctl list | grep -i 'hermes.*web\|web.*hermes' || true
```

## Fix pattern

1. Back up `~/.hermes-web-ui/config.json`.
2. Add/update `modelVisibility["custom:<provider_name>"]` with the exact model id.
3. Back up and remove stale `~/.hermes-web-ui/cache/provider-model-catalog.json`.
4. Restart the Web UI service, commonly:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.webui
```

5. Verify port 8648 is listening and the cache regenerated with the expected provider/model.
6. Ask the user to refresh/reopen Desktop/Web UI and preferably start a new session; existing sessions may remain bound to their original model/provider.

## Pitfalls

- Existing sessions can stay bound to their original model even after a bottom-selector change. New session testing is cleaner.
- Web UI may have its own model visibility config and provider catalog cache independent of Hermes core config.
- Do not print API keys when probing direct provider APIs.
