# Gateway/Profile Hygiene Session Note — 2026-05-29

## Context

After a Hermes upgrade, live checks showed the default gateway eventually loaded, but many non-default profiles (`deepseekv4` and `pgg-*`) also had gateway services running. This conflicted with the user's architecture: Feishu/Lark ingress should be handled only by the `default` profile; department profiles should be used as workers/dispatch targets, not independent messaging gateways.

## Useful command sequence

### Check status

```bash
hermes gateway status
hermes gateway list
hermes profile list
hermes config check
hermes doctor
```

### Stop and uninstall non-default gateways

```bash
profiles='deepseekv4 pgg-anguan pgg-feisu pgg-guwen pgg-law pgg-minshi pgg-shenji pgg-tuiyan pgg-wenshu pgg-xingshi pgg-xunshi pgg-zhengju pgg-zhinao pgg-zhixing'
for p in $profiles; do
  hermes --profile "$p" gateway stop || true
  hermes --profile "$p" gateway uninstall || true
done
hermes gateway start
```

### Archive stale LaunchAgent backups

```bash
archive="$HOME/.hermes/archives/launchagents-gateway-backups-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$archive"
for f in "$HOME"/Library/LaunchAgents/ai.hermes.gateway*.plist.bak_*; do
  [ -e "$f" ] || continue
  mv "$f" "$archive/"
done
```

### Migrate config

```bash
cfg="$(hermes config path)"
cp "$cfg" "$cfg.bak-v$(date +%Y%m%d-%H%M%S)"
hermes config migrate
hermes config check
```

### Inspect profile env safely

```bash
python3 - <<'PY'
from pathlib import Path
import re
base=Path.home()/'.hermes/profiles'
for p in sorted(x for x in base.iterdir() if x.is_dir()):
    env=p/'.env'; cfg=p/'config.yaml'
    keys=[]
    if env.exists():
        for line in env.read_text(errors='ignore').splitlines():
            m=re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
            if m: keys.append(m.group(1))
    risky=[k for k in keys if 'FEISHU' in k.upper() or 'LARK' in k.upper()]
    print(p.name, 'config=', cfg.exists(), 'env=', env.exists(), 'env_keys=', len(keys), 'feishu_lark_keys=', risky)
PY
```

## Specific fixes made in the session

- Migrated main config from v23 to v24, with backup first.
- Stopped and uninstalled non-default gateway services.
- Archived 15 stale gateway backup plists.
- Repaired `pgg-wenshu`, which had profile state but lacked `config.yaml` and `.env`, by seeding from a standard department profile and verifying no Feishu/Lark keys existed.
- Created missing alias for `pgg-zhixing`.
- Installed Playwright Chromium to restore ordinary `browser` tool availability.
- Installed `cua-driver 0.3.2` to restore `computer_use` availability.

## Final expected shape

```text
Gateways:
  ✓ default (current) — PID <pid>
  ✗ deepseekv4        — not running
  ✗ pgg-*             — not running

LaunchAgents:
  ai.hermes.gateway.plist

Doctor:
  ✓ Config version up to date
  ✓ browser
  ✓ computer_use
```

Remaining doctor warnings for missing external API keys/OAuth are not local hygiene failures; classify them as user/API setup requirements.
