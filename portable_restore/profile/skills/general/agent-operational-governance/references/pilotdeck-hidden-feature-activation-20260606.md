# PilotDeck hidden-feature activation evidence gate（2026-06-06）

## Trigger

Use this reference when the user asks to unlock, activate, verify, or absorb PilotDeck “hidden features” / 总纲3 capabilities, especially modules such as Router Orchestrator, Token Saver, Custom Router, Permission, MCP, Always-On, Workspace Provider, Gateway, and SubAgent.

## Core lesson

Do not collapse four different states into one word “active”. For PilotDeck, every feature must be classified separately by:

1. Source exists — e.g. `src/router/tokenSaver` or `src/mcp` exists.
2. Config enabled — e.g. `router.tokenSaver.enabled=true` or `alwaysOn.enabled=true`.
3. Runtime smoke — Gateway/WS/API/module actually loads and responds.
4. Evidence-chain settled — report + manifest/readback record exists.

Only call a feature PASS when the relevant runtime smoke succeeded. Otherwise use WATCH or BLOCKED.

## Known PilotDeck paths

- Remote repo: `https://github.com/OpenBMB/PilotDeck`
- Local repo: `~/.pilotdeck-agi/PilotDeck`
- Active config: `~/.pilotdeck/pilotdeck.yaml`
- Hidden config: `~/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`
- Gateway health: `http://127.0.0.1:18789/health`
- Gateway WebSocket: `ws://127.0.0.1:18789/ws`
- Gateway token: `~/.pilotdeck-agi/home/.pilotdeck/server-token`

HTTP `/api/config` is not the Gateway protocol surface; use `/health` for HTTP readiness and the WebSocket protocol for methods such as `reload_config`, `list_projects`, `cron_list`, `skill_list`, and `describe_project`.

## Safe activation pattern

1. Read remote HEAD / local git status, but do not pull/merge unless explicitly asked.
2. Back up both active configs before edits.
3. Enable only schema-supported fields:
   - `router.autoOrchestrate`
   - `router.tokenSaver`
   - `router.zeroUsageRetry`
   - `router.transientRetry`
   - `router.fallback`
   - `router.stats`
   - `alwaysOn`
   - `cron`
4. Keep Always-On autonomous timer off unless the user explicitly authorizes unattended background actions:
   - `alwaysOn.enabled=true`
   - `alwaysOn.trigger.enabled=false`
5. Run `npm run build` after code/config changes.
6. Restart via the existing PilotDeck wrapper so `.env` and `PILOT_HOME` are loaded:
   - `~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_second_agi.sh`
7. Verify with Gateway WS, not only port/process state.
8. Generate a report under Hermes governance workspace and update `EVOLUTION_MANIFEST.json`.

## Custom Router resolution

Disk-loaded `plugin.json` plugins cannot provide function-valued `routerContributions`. The source states programmatic contributions are only available to builtin or test-injected plugins. A safe smoke activation can add a minimal builtin contribution such as `pilotdeck-smoke-router` that only acts on a tagged message like `[pilotdeck-custom-router-smoke]`; otherwise it returns `undefined` and normal routing is untouched.

A valid smoke must show:

- `PluginRuntime.lookupRouter('pilotdeck-smoke-router')` returns a router.
- `RouterRuntime.decide()` on a tagged request returns `resolvedFrom='custom'`.
- Normal untagged routing is not changed.

## Permission resolution

Use `permissions.json` and PilotDeck’s own permission utilities for a non-destructive smoke:

- `readPermissionSettings()`
- `permissionSettingsToRuleSet()`

A safe default is:

- `skipPermissions=false`
- allow read/search/skill tools and read-only bash such as `pwd`, `ls*`, `git status*`
- deny destructive bash patterns such as `rm*`, `sudo*`, and shell-piped remote scripts

Do not execute destructive tools just to prove the permission layer.

## MCP resolution

For a low-risk PASS, configure a local stdio MCP server with one read-only static tool and verify through PilotDeck runtime:

- `loadMcpServerConfig()`
- `parsePluginMcpServers()`
- `new McpRuntime(...).start()`
- `listAllTools()` includes the expected tool

If the MCP server script imports `@modelcontextprotocol/sdk`, place/run it from the PilotDeck repo so Node can resolve `node_modules`, or otherwise set module resolution correctly. A successful smoke should show server status `ready` and a listed wire tool such as `mcp__pilotdeck-readonly-smoke__pilotdeck_smoke_status`.

## Pitfalls

- Do not claim `src/evolution` is active if the current OpenBMB/PilotDeck tree lacks `src/evolution`. Mark it BLOCKED or map it only to existing `router.scenarios.evolution` semantics.
- Do not treat `/api/config` 404 as Gateway failure; PilotDeck Gateway uses WebSocket for most methods.
- Do not start PilotDeck with a stripped environment; missing provider env vars can abort config loading. Use the wrapper or source the correct `.env`.
- Do not mark Always-On full execution PASS merely because `always_on_apply` is reachable. If it returns `cycle_not_found`, runtime is mounted but a valid work cycle is still required.
