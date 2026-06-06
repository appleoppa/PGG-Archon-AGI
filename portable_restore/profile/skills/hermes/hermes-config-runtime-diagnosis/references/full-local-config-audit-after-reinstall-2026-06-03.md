# Full local Hermes config audit after reinstall / duplicate install

Use when the user has an existing local Hermes Agents deployment and installs another Hermes Agent, then asks whether configuration was migrated or wants the current situation confirmed.

## Durable lesson

Do **not** equate “new Hermes CLI reads `~/.hermes/config.yaml`” with “all configuration/capabilities migrated.” Treat it as a runtime reuse/migration audit problem and verify config, profiles, services, providers, cron, Web UI, session DB, and overlays separately.

## Audit dimensions

1. **Install identity**
   - `which -a hermes`
   - `hermes --version`
   - `hermes config path`
   - `hermes config env-path`
   - pip package location / project root, without printing secrets.

2. **Config + provider alignment**
   - Parse `~/.hermes/config.yaml` and all `~/.hermes/profiles/*/config.yaml`.
   - Record `_config_version`, default model/provider, profile model/provider.
   - Summarize provider `name`, `model`, `api_mode`, `base_url`, `key_env`; only report whether the key exists, never the key value.
   - Smoke-test providers using each provider’s real API shape: `codex_responses` for GPT/Claude custom providers; `chat_completions` for DeepSeek-like providers. Use enough token budget for reasoning models.

3. **Runtime services**
   - `hermes profile list`
   - `hermes gateway status`
   - `launchctl list | grep -i hermes`
   - process scan for `hermes`, profile gateways, Web UI bridge, and evolution watcher.
   - Web UI: check running process and HTTP `/health` endpoint if a port is visible; do not rely only on CLI availability.

4. **Persistence and scheduled work**
   - Session DB canonical path is `~/.hermes/state.db`; run SQLite `PRAGMA integrity_check`.
   - Read `~/.hermes/cron/jobs.json`; list active/error jobs and verify script existence under `~/.hermes/scripts/`.
   - For cron failures, classify as missing old module, missing script, timeout, provider/network, or current import/path mismatch.

5. **Overlay / repo hygiene**
   - Run git status inside `~/.hermes/hermes-agent`.
   - Large untracked overlays (`agent/pgg_archon_*.py`, `agent/apex_*.py`, `apex_god/`, custom tools/tests) mean the repo is not clean. Do not delete or restore automatically; first classify official repo vs active overlay vs historical residue.
   - Avoid `hermes update` on a dirty overlay-heavy repo until backup/classification is done.

6. **Evolution module split-brain**
   - Distinguish Rust-native daemon/binary health from Python module availability.
   - A running `apex13 fused-watch` process does not prove `import hermes_apex_evolution` works in the active Hermes venv.
   - Verify both the launchd daemon and the Python import path when cron/tools depend on the module.

## Reporting contract

Return a concise status report:

- `status`: runnable / partially healthy / blocked
- `evidence`: paths, version, profile count, gateway/Web UI health, session DB integrity, provider smoke results
- `risks`: cron failures, overlay conflicts, missing imports, dirty repo, version drift
- `migration_conclusion`: distinguish config reuse, profile migration, provider usability, and capability migration
- `next_fix_order`: backup → env/path cleanup → module import repair → cron repair → overlay classification → update

## Pitfalls

- Do not print `.env` secrets.
- Do not mark optional missing OAuth/API keys as failures if active custom providers smoke-test successfully.
- Do not state “fully migrated” without a source baseline or explicit old-install comparison.
- Do not hard-code one session’s missing binaries or paths as durable facts; capture the audit/fix pattern instead.
