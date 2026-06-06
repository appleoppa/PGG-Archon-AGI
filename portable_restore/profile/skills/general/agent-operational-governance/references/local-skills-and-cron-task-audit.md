# Local Skills and Cron Task Audit Pattern

## When to use

Use this reference when the user asks to audit local skills, skill library health, Hermes tasks, cron jobs, or background task queues.

## Audit scope

Check these sources together; no single file is the complete task truth source:

1. `~/.hermes/skills/**/SKILL.md` for file-level skill inventory.
2. `hermes skills list` for runtime-visible/enabled skill inventory.
3. `~/.hermes/cron/jobs.json` and `hermes cron list` for scheduled tasks.
4. `~/.hermes/cron/output/` for actual recent side-effect evidence.
5. `~/.hermes/workspace/任务队列/` for manual/case-style queued tasks.
6. `~/.hermes/workspace/审计队列/` and `~/.hermes/workspace/监控日志/` for governance evidence.

## Key checks

- Compare raw `SKILL.md` count with `hermes skills list` count. A mismatch may be expected if archived or hidden skill files exist, but it should be reported.
- Detect duplicate `name:` frontmatter values, especially under `.archive/` where a copied `SKILL.md` can keep producing duplicate-skill false positives.
- Scan for malformed frontmatter, very large skill files, empty support directories, and possible secret patterns. Redact all secret-looking values in outputs.
- Manually inspect secret-pattern hits before calling them leaks: examples such as `api_key: ...`, `TOKEN=$(cat ...)`, `task-001`, or checklist text are often false positives.
- For cron jobs, verify both scheduler state and output evidence. `Last run: ok` is not enough by itself.
- Resolve relative `script` paths against likely locations: job workdir, `~/.hermes/`, and `~/.hermes/scripts/` before reporting a missing script.
- Check whether cron job names match actual schedule expressions. Name/schedule drift causes bad operational judgments even when tasks run successfully.
- Check `schedule.expr`, `schedule.display`, `schedule.spec`, and `schedule_display` together. If they disagree, align them before trusting CLI display or next-run forecasts.
- When changing a cron expression directly in `jobs.json`, also refresh or recompute `next_run_at`; otherwise `hermes cron list` can show the new schedule with a stale next-run timestamp. Re-run `hermes cron list` after the edit and verify both `Schedule` and `Next run`.
- Treat empty `workspace/任务队列` as only one signal. Periodic/background tasks may live entirely in cron and `cron/output/`.
- Maintain a local task truth-source note when multiple queues exist: cron for scheduled/background tasks, `workspace/任务队列` for manual/case-style queued tasks, `workspace/审计队列` for governance evidence.

## Common findings and recommended actions

- **Archived duplicate skill:** rename archived `SKILL.md` to `SKILL.md.archived` or delete only after confirming the archive is no longer needed.
- **Cron name/frequency mismatch:** prefer renaming the cron job first if actual cadence appears intentional; changing the schedule is higher impact.
- **Legacy naming:** distinguish historical compatibility references from current naming. Keep valid historical context, but do not let new user-visible reports expand old names.
- **Silent watchdog output:** empty cron output can be normal for watchdog-style tasks; do not treat it as failure without additional evidence.

## Report shape

Write a concise audit report under `workspace/审计队列/` with:

- status and evidence level;
- counts for raw skills, visible skills, cron jobs, active cron jobs, task queue files;
- P0/P1/P2 findings;
- normal items verified;
- recommended remediation order;
- explicit boundary: whether content quality of each skill/task was reviewed or only inventory/runtime health was audited.
