# Hermes/PGG Portable Restore GitHub Migration Pattern

## Trigger

Use when the user asks whether the current local Hermes/PGG Archon evolution state can be deployed to a remote GitHub repository so a new computer can clone and restore the current state.

## Core lesson

Do **not** push `~/.hermes` wholesale. Build a GitHub-safe portable restore skeleton, verify it locally, then verify it from a fresh remote clone. A local rsync simulation can pass while a remote clone fails if `.gitignore` excludes required files such as `data/*`.

## Safe restore bundle shape

Recommended repo subtree:

```text
portable_restore/
  README.md
  bootstrap/install_macos.sh
  bootstrap/restore_profile.sh
  bootstrap/verify_runtime.sh
  config-templates/env.example
  config-templates/config.yaml.template
  docs/INCLUDE_MANIFEST.json
  docs/SECURITY.md
  profile/SOUL.md
  profile/memories/MEMORY.md
  profile/memories/USER.md
  profile/data/EVOLUTION_MANIFEST.json
  profile/skills/
```

## Exclude from GitHub

Never commit real values or runtime-heavy local state:

- `.env`, `auth.json`, OAuth sessions, secrets, credential stores, API keys.
- `venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `target/` build outputs.
- Legal case materials and privileged client files.
- Large workspace logs/caches unless deliberately redacted and classified.

## Required verification gates

1. Generate/refresh `portable_restore/` from live profile files.
2. Redact token/hash/secret-like fields and replace placeholder session tokens in portable copies.
3. Run a staged secret scan; treat placeholder tokens as risks unless explicitly replaced with `<LOCAL_..._PLACEHOLDER>`.
4. Run `bash -n` for restore/verify/install scripts and `git diff --check`.
5. Local simulated restore:

```bash
TARGET_HOME=/tmp/pgg-archon-restore-home bash portable_restore/bootstrap/restore_profile.sh
TARGET_HOME=/tmp/pgg-archon-restore-home bash portable_restore/bootstrap/verify_runtime.sh
```

6. Push to a non-main migration branch first.
7. Fresh remote clone verification:

```bash
git clone --branch <branch> --single-branch https://github.com/appleoppa/PGG-Archon-AGI.git /tmp/pgg-archon-remote-clone
TARGET_HOME=/tmp/pgg-archon-remote-home bash portable_restore/bootstrap/restore_profile.sh
TARGET_HOME=/tmp/pgg-archon-remote-home bash portable_restore/bootstrap/verify_runtime.sh
```

## Critical pitfall

If the repo `.gitignore` contains broad patterns such as `data/*`, `portable_restore/profile/data/EVOLUTION_MANIFEST.json` may be missing from the remote clone even when local tests passed. Add explicit exceptions or `git add -f` and verify via fresh remote clone.

## Completion language

Allowed: “Portable restore skeleton verified from remote clone.”

Not allowed: “100% state restored” unless secrets, OAuth sessions, keychain, case files, local DBs, venv/node_modules, and external service authorizations are also restored and verified. Usually report this boundary explicitly.
