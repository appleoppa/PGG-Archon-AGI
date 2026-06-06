# PilotDeck default-entrypoint drift and model-pool preservation — 2026-06-03

## Trigger

Use when PilotDeck appears configured in the hidden deployment directory but opening `PilotDeck.app` or the Web UI still shows onboarding / “configure LLM”, or when provider cleanup accidentally removes useful no-tools models.

## Durable lesson

PilotDeck can have two different config homes:

- intended hidden deployment: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`
- default app path: `/Users/appleoppa/.pilotdeck/pilotdeck.yaml`

If `PilotDeck.app` starts without `PILOT_HOME` / `PILOTDECK_CONFIG_PATH`, it may read the default app path. If that path contains the bootstrap placeholder provider (`_placeholder`, `PLACEHOLDER_RUN_ONBOARDING_TO_REPLACE`), the UI will ask the user to configure LLM even though the hidden deployment is already configured.

## Diagnosis checklist

1. Compare live API config with the intended file:
   - `GET http://127.0.0.1:3001/api/config`
   - inspect `path`, provider ids, `agent.model`, and whether `_placeholder` appears.
2. Inspect projects path:
   - `GET http://127.0.0.1:3001/api/projects`
   - ensure `general.fullPath` points at the intended hidden home.
3. Check active process env only for key presence / paths, never print secret values.
4. Inspect onboarding state in the auth DB if the UI still redirects:
   - `auth.db` table `users.has_completed_onboarding`.

## Fix pattern

When the default path is only a placeholder and the user wants the hidden PilotDeck deployment to be authoritative:

1. Backup the placeholder default home, e.g. `.pilotdeck.placeholder-backup-<timestamp>`.
2. Replace `/Users/appleoppa/.pilotdeck` with a symlink to `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck`.
3. Mark local onboarding complete in the actual auth DB if appropriate.
4. Restart PilotDeck gateway, UI server, and Vite client.
5. Re-read `/api/config` and `/api/projects`; verify no `_placeholder` and the hidden path is active.

## Model-pool preservation pitfall

Do not “fix” a tools-routing error by deleting every no-tools provider from the model pool. Preserve useful chat/auditor models (e.g. Agnes chat-only or MIMO auditor) unless the user explicitly asks to delete them. The correct separation is:

- agent/tool-use route and fallback: only models verified to support tools.
- model pool: may include no-tools models with `supportsToolUse: false` for chat-only/auditor use.
- router tokenSaver tiers: must not select no-tools models for agent requests that include tools.

If the user later changes the desired main LLM, re-test the candidate model with a direct tools smoke test before setting `supportsToolUse: true` or routing agent tasks to it.

## Verification evidence shape

Report:

```text
config_path: <path returned by /api/config>
providers: [...]
agent: provider/model
placeholder_present: true|false
projects_general_path: <path>
onboarding: [(username, has_completed_onboarding)]
router_last_decision: provider/model
turn_result: success completed
```
