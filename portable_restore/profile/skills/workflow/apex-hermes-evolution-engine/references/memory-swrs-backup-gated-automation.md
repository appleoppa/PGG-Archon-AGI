# Memory SWRs automation: backup-gated write/apply pattern

Session-derived reusable pattern for turning a dry-run memory consolidation system into safe scheduled automation.

## Trigger

Use when enabling automatic memory consolidation, duplicate removal, or scheduled memory replay for Hermes.

## Safety posture

Default progression:

```text
dry-run scorer → backup gate → dry-run apply → scheduled dry-run → observed safe runs → optional real --apply
```

Do not jump directly from candidate scoring to durable memory writes.

## Backup gate

Before any real memory write or de-duplication:

- Back up memory/user files and related memory indexes/databases.
- Run backups at least twice daily, e.g. 09:00 and 21:00.
- Retain backups for at least 7 days; use 8 days as safer default.
- Prune only timestamp-patterned backup directories under the dedicated memory backup root.
- Refuse real apply if no fresh backup exists, e.g. within the last 24 hours.

Recommended backup root:

```text
~/.hermes/backups/memory_swrs/YYYYMMDD_HHMMSS/
```

## Apply gate

Automatic writes are only acceptable for narrow low-risk candidates:

- target is `memory` or `user`, not `skill`, config, source, or credentials;
- score is high, e.g. `>= 7`;
- content is declarative, stable, and useful after 7 days;
- no secrets, tokens, credentials, PR/commit/issue IDs, temporary progress, or completion logs;
- exact duplicate check passes;
- source evidence is recorded;
- backup gate passes.

Workflow/procedure candidates should become skill patches or review items, not memory entries.

## Duplicate deletion gate

Automatic deletion should be limited to exact duplicate non-heading lines within the same target memory file. Do not automatically delete:

- semantic duplicates with different wording;
- cross-file near-duplicates;
- old/new rule conflicts;
- path/config/model/profile rules that may differ by context;
- anything not backed up and logged.

## Cron layout

Safe first deployment:

| Time | Job | Mode |
|---|---|---|
| 09:00 | memory backup | no-agent/local |
| 21:00 | memory backup | no-agent/local |
| 21:10 | SWRs replay/candidate generation | no-agent/local |
| 21:15 | SWRs apply dry-run | no-agent/local |

Only after observing several safe dry-run reports should the apply job be switched to real `--apply`.

## Verification

After deployment, verify:

- scripts exist and are executable;
- a backup was actually created and contains a manifest;
- dry-run apply reports backup gate status;
- cron list shows all jobs enabled with expected schedules;
- any gene/log/report says whether real writes/deletes are enabled or still dry-run.

## Boundary wording

Use accurate completion language:

```text
backup automation enabled;
replay automation enabled;
dry-run apply enabled;
real memory writes/deletions not enabled yet.
```

Do not say automatic durable memory writes are active until a real `--apply` cron/script has been enabled and verified.
