# Post-install overlay soft-archive + update preflight pattern — 2026-06-03

## When to use

Use after a Hermes reinstall/update or duplicate install where the active repo has many untracked PGG/APEX/local overlay files, runtime wrappers may not expose expected tools in non-interactive shells, and the user wants repair before running `hermes update`.

## Scope and safety

- Treat this as a reversible runtime hygiene workflow, not a cleanup-by-deletion task.
- Do not restore deleted legacy Python modules just to silence old cron/import errors.
- Do not delete overlay files until there is a manifest, hash evidence, reference scan, archive copy, and an observation period.
- Never print secrets from `.env` or config backups.

## Workflow

1. **Backup first**
   - Back up active `config.yaml`, `.env`, cron `jobs.json`, wrappers, and repo status into `~/.hermes/workspace/治理/hermes-repair-backups/<timestamp>/`.

2. **Fix non-interactive wrapper PATH by injecting PATH, not by assuming the login shell**
   - If doctor/web-ui/cron cannot find already-installed tools such as Node.js or ripgrep, patch the active wrapper under `~/.local/bin/` to export a full deterministic PATH before `exec`.
   - Typical macOS Hermes PATH segments: `~/.local/bin`, `~/.hermes/node/bin`, `~/.npm-global/bin`, `/usr/local/bin`, `/opt/homebrew/bin`, `/usr/bin`, `/bin`.
   - Verify with `hermes doctor`; the lesson is the wrapper PATH fix, not the transient missing-tool symptom.

3. **Classify untracked overlay files**
   - Use git status plus a manifest script to classify untracked items into buckets such as `apex_python_overlay`, `pgg_archon_python_overlay`, `se20_eval_overlay`, `runtime_manifest_or_bootstrap`, and `other_untracked`.
   - Compute hashes and sizes. Search for active registrations/imports before deciding that an overlay is inactive.

4. **Soft-archive, source left in place**
   - Copy every overlay item into `~/.hermes/workspace/治理/hermes-overlay-archive/<timestamp>/files/`.
   - Write an `ARCHIVE_MANIFEST.json` with count, hashes, category, and policy such as `COPY_ONLY_SOURCE_LEFT_IN_PLACE`.
   - Add exact overlay paths to `.git/info/exclude` so the local repo becomes clean without deleting source files or altering tracked history.

5. **Update preflight instead of direct update**
   - Run `git fetch --prune origin`.
   - Record local HEAD, `origin/main`, ahead/behind count, incoming commit list, and changed files into `~/.hermes/workspace/治理/hermes-full-config-audit/hermes_update_preflight_diff_<timestamp>.txt`.
   - Defer `hermes update` if the diff includes runtime/server/desktop/i18n/installer changes and the user did not explicitly authorize update execution.

6. **Verify live runtime after hygiene**
   - `git status --short` should be clean.
   - `hermes doctor` should show core external tools OK; optional provider/credential warnings must be separated from runtime blockers.
   - Verify `hermes-web-ui status`, `hermes gateway status`, selected cron `last_status`, and any Rust evolution module import/API smoke if that module is part of the deployment.
   - Write and read back a final verification file under `~/.hermes/workspace/治理/hermes-full-config-audit/`.

## Report contract

Report in short field blocks:

- `status`
- `fixed`
- `left_in_place`
- `evidence_paths`
- `remaining_warnings`
- `next_safe_step`

## Pitfalls

- A clean `git status` after `.git/info/exclude` does **not** mean files were deleted or migrated; explicitly state source files remain.
- A direct script success does not update cron scheduler state; use `hermes cron run` / `cron tick` when scheduler state matters.
- Standard doctor warnings for a provider may refer to a different built-in provider key than a working custom provider; verify exact provider key/env before declaring failure.
- Do not turn fresh-install PATH mismatches into durable claims that a tool is broken. Capture and apply the deterministic wrapper PATH repair instead.
