# Hermes/PGG portable restore via private GitHub — verification pattern

Use when asked whether a local Hermes/PGG evolution state can be moved to a private GitHub repo so a new computer can clone and restore it.

## Core lesson

Do not treat `git push` or a local rsync copy as proof of portability. The completion gate is a fresh remote clone from GitHub into a clean temp directory, followed by restore and verify scripts against an isolated `TARGET_HOME`.

## Recommended restore-bundle shape

Create a class-level portable bundle such as:

```text
portable_restore/
  README.md
  bootstrap/
    install_macos.sh
    restore_profile.sh
    verify_runtime.sh
  config-templates/
    config.yaml.template
    env.example
  docs/
    INCLUDE_MANIFEST.json
    SECURITY.md
  profile/
    SOUL.md
    memories/
      MEMORY.md
      USER.md
    data/
      EVOLUTION_MANIFEST.json
    skills/
```

Include source/code changes that are part of the current runtime state, but do not include live credentials, OAuth sessions, `venv/`, `node_modules/`, caches, raw case materials, or large workspaces.

## Gates

1. Create a new migration branch. Do not push to or overwrite remote `main`/default branch unless explicitly authorized.
2. Copy only portable state: SOUL, curated memories, skills, selected manifests, templates, and bootstrap scripts.
3. Redact or remove secret-like fields from manifests and references. Hashes of tokens may still be sensitive enough to redact when not necessary for restore.
4. Run secret scan over the staged bundle. Treat examples/placeholders conservatively: replace realistic-looking tokens with obvious placeholders such as `<LOCAL_SESSION_TOKEN_PLACEHOLDER>`.
5. Run script syntax checks and `git diff --cached --check`. If imported skill snapshots have old CRLF/trailing whitespace, normalize only the portable copy, not the live skill library.
6. Run a local isolated restore smoke:

```bash
TARGET_HOME=/tmp/pgg-archon-newhome bash portable_restore/bootstrap/restore_profile.sh
TARGET_HOME=/tmp/pgg-archon-newhome bash portable_restore/bootstrap/verify_runtime.sh
```

7. Commit and push the migration branch.
8. Perform the decisive proof: fresh clone from the private GitHub branch, then run restore/verify again against a clean `TARGET_HOME`.

## Important pitfall: `.gitignore` can invalidate local proof

A local rsync/copy restore can pass even when GitHub clone will fail because files under ignored paths were never tracked. In this session, `portable_restore/profile/data/EVOLUTION_MANIFEST.json` was omitted by a broad `data/*` ignore rule. Fix with explicit exceptions or force-add the needed file, then rerun the remote clone proof:

```gitignore
# Portable restore exceptions
!portable_restore/profile/data/
!portable_restore/profile/data/EVOLUTION_MANIFEST.json
```

Then verify:

```bash
git clone --branch <migration-branch> --single-branch <private-repo-url> /tmp/pgg-archon-remote-clone
TARGET_HOME=/tmp/pgg-archon-remote-home bash /tmp/pgg-archon-remote-clone/portable_restore/bootstrap/restore_profile.sh
TARGET_HOME=/tmp/pgg-archon-remote-home bash /tmp/pgg-archon-remote-clone/portable_restore/bootstrap/verify_runtime.sh
```

## Truthful boundary wording

A PASS means the governed Hermes/PGG skeleton is restorable: rules, skills, curated memory, selected manifests, and tracked source state. It does not restore real API keys, OAuth sessions, macOS Keychain, local venv/node_modules, privileged case files, or external service authorization. Report those as required local rehydration steps, not as failures of the GitHub bundle.
