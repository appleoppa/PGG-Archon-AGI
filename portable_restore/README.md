# PGG Archon / Hermes Portable Restore

Generated: 2026-06-06T14:15:31

This directory stores a sanitized, GitHub-safe restore skeleton for Apple Didi / PGG Archon Hermes Agent state.

## What is included

- `profile/SOUL.md`
- `profile/memories/MEMORY.md`
- `profile/memories/USER.md`
- `profile/data/EVOLUTION_MANIFEST.json`
- `profile/skills/`
- `config-templates/`
- `bootstrap/install_macos.sh`
- `bootstrap/restore_profile.sh`
- `bootstrap/verify_runtime.sh`

## What is intentionally excluded

- `.env`, `auth.json`, tokens, secrets, OAuth sessions
- `venv/`, `node_modules/`, `__pycache__/`
- case materials and privileged legal files
- large runtime caches and logs

## Restore on a new Mac

```bash
git clone <PRIVATE_REPO_URL> PGG-Archon-AGI
cd PGG-Archon-AGI/portable_restore
DRY_RUN=1 bash bootstrap/install_macos.sh
bash bootstrap/restore_profile.sh
bash bootstrap/verify_runtime.sh
cp config-templates/env.example ~/.hermes/.env
# Fill secrets locally; never commit real values.
```

## Completion boundary

This restores the governed Hermes/PGG state skeleton. Provider credentials and OAuth sessions must be re-entered or restored from a separate encrypted backup.
