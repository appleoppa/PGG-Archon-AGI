# File System Management — Absorbed Detail

Original skill: `file-system-management`.

## Root vs Workspace

Root is for system/runtime/config. Work product belongs in `~/.hermes/workspace/`.

Allowed root classes: config, env/auth/state DBs, sessions, cron, logs, skills, memories, cache, profiles, hooks, temp, gateway files, source package.

Workspace active classes: AGENTS/MEMORY/TOOLS/SOUL/USER/IDENTITY, 智库, 向量库, 开智, 办案库, config, scripts, tools, workflows, standards, templates, logs, queues, audit queues, archives, monitoring logs.

## Cleanup Pattern

1. Establish protected asset allowlist.
2. Bucket candidates: active assets / historical archive / junk.
3. Delete only low-risk junk after confirmation, e.g. `.DS_Store`, temp/swap files, empty shells.
4. Archive one-time scripts, old prototypes, obsolete migration helpers, historical backups.
5. Preserve relative paths under `workspace/存档/<topic>/<timestamp>/moved/`.
6. Verify protected asset existence/counts, SQLite tables/rows, root clutter, `.DS_Store`, and archive completeness.

## Special Boundaries

- `开智/` active directory should not keep per-round process folders long-term.
- Historical APEX formula directories such as `开智核心/` and `01-APEX开智/` can be archived only after confirming zero runtime dependency.
- Gene DBs, vector libraries, guiding-case libraries, legal/regulatory libraries, case-management libraries, and gene output directories are protected assets.

## Secret Leak Hygiene

- Default scope: `~/.hermes` unless full-disk scan requested.
- Never print raw secrets.
- `.env` with `0600` is normal secret store.
- Configs, logs, sessions, request dumps, archive backups are leakage surfaces.
- Before redaction, create remediation backup.
- Convert active config plaintext keys to env references; verify permissions and rescan.

## Verification Checklist

- Work files stayed under workspace.
- Root not polluted.
- Destructive operation had content inspection.
- Important edits had archive backup.
- Stale references checked after structural changes.
