# Hermes post-install migration and runtime repair — 2026-06-03

## Scenario

A user has an existing local Hermes multi-profile deployment and installs/updates another Hermes Agent instance. The CLI may point to the new runtime while still reading the old `~/.hermes` configuration. The durable lesson is not that any one path is broken, but the repair workflow for mixed install/config/runtime states.

## Safe sequence

1. Load `hermes-agent` and `hermes-config-runtime-diagnosis`.
2. Establish scope and active paths without printing secrets:
   - `command -v hermes`, `hermes --version`, `hermes config path`, `hermes config env-path`.
   - `hermes profile list`, `hermes status`, `hermes gateway status`, `hermes doctor`.
3. Back up before edits:
   - config, `.env`, cron jobs, LaunchAgents snapshot, status/doctor outputs, git status.
4. Fix reversible runtime defects first:
   - quote shell-sensitive `.env` values with spaces;
   - restore missing CLI symlinks only when target package/bin exists;
   - install local compiled extension modules into the active venv and verify import/API.
5. Cron repair principle:
   - run known-good scripts directly, then trigger through `hermes cron run <id>` + `hermes cron tick` so `last_status` is refreshed by the scheduler;
   - pause and rename old jobs that depend on removed/replaced modules rather than resurrecting obsolete modules.
6. Overlay governance:
   - never delete untracked historical overlay immediately;
   - create an overlay manifest with categories, reference scans, and `manifest_only_no_delete` actions;
   - only after no-reference verification should soft-archive, observe, then hard-delete.
7. Cross-verify significant repair decisions with a real secondary model call when the user asks; record provider/model/endpoint/status and visible output path.

## Verification handles

A complete repair should include at least:

- `source ~/.hermes/.env` succeeds in a subshell.
- `python -c 'import hermes_apex_evolution as m; print(m.version())'` or equivalent extension import succeeds when relevant.
- `hermes-web-ui status` or the correct Web UI health endpoint shows running if Web UI is in scope.
- `hermes gateway status` shows the default and expected profiles running.
- Target cron jobs have fresh `last_status=ok` after `hermes cron run` + `hermes cron tick`, not just direct script success.
- `hermes doctor` core checks are green; optional missing providers/tools are labeled optional, not treated as failures.

## Pitfalls

- Do not claim “migration complete” without comparing current runtime against source/old config or at least classifying unknowns.
- Do not restore deleted Python APEX/PGG modules just to satisfy old cron imports if a Rust/native replacement is now the intended path.
- Do not clear cron errors with blind file edits; use scheduler execution to refresh where possible, and preserve historical evidence.
- Do not run `hermes update` into a repo with unclassified untracked overlays; first manifest and back up.
- Do not encode transient command-not-found or missing credential facts as durable skill rules; encode the repair pattern instead.
