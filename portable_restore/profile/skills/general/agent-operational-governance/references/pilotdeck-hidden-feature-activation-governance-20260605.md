# PilotDeck hidden-feature activation governance — 2026-06-05

## Trigger

Use when the user asks to read OpenBMB/PilotDeck, compare a local PilotDeck deployment with GitHub, or activate “hidden/deep” PilotDeck features such as router orchestration, token saver, retry/fallback/stats, Always-On, Cron, MCP, permissions, workspace providers, or custom router.

## Core lesson

Do not treat a source directory or config key as proof of an active feature. Keep four states separate:

1. **Source exists** — directory/file exists in `~/.pilotdeck-agi/PilotDeck/src/...` or upstream GitHub.
2. **Config enabled** — active config path contains a schema-valid enabled setting.
3. **Runtime reachable** — gateway/WS method or subsystem is mounted and responds.
4. **Evidence-chain complete** — smoke output, report path, and manifest entry exist.

Only call a feature active when config + runtime evidence both exist. Mark as WATCH when source exists but plugin/server/scenario smoke is missing. Mark as BLOCKED when the source path is absent in the current upstream/local tree.

## Durable findings from this session

Remote repo:

```text
https://github.com/OpenBMB/PilotDeck
```

Local deployment:

```text
/Users/appleoppa/.pilotdeck-agi/PilotDeck
/Users/appleoppa/.pilotdeck/pilotdeck.yaml
/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml
```

Gateway facts:

- HTTP `/health` is valid.
- HTTP `/api/config`, `/api/projects`, etc. are not the right contract for the local gateway.
- Business methods use WebSocket protocol at `ws://127.0.0.1:18789/ws`.
- Token path is `<PILOT_HOME>/server-token`; do not print it.

Schema-backed low-risk activation knobs:

```yaml
router:
  autoOrchestrate:
    enabled: true
    triggerTiers: [complex]
    allowedTools: [agent, read_file, grep, glob, read_skill]
    slimSystemPrompt: true
    subagentMaxTokens: 48000
  tokenSaver:
    enabled: true
  zeroUsageRetry:
    enabled: true
    maxAttempts: 2
  transientRetry:
    enabled: true
    maxAttempts: 2
    baseDelayMs: 500
    maxDelayMs: 4000
  stats:
    enabled: true

alwaysOn:
  enabled: true
  trigger:
    enabled: false   # keep autonomous timer off unless explicitly authorized

cron:
  enabled: true
  timezone: Asia/Shanghai
  maxConcurrentRuns: 1
```

## 15-feature status pattern

In the verified local tree, 11/15 could be activated or reached, 3 stayed WATCH, 1 was BLOCKED:

- PASS: Always-On source/config surface, Router Orchestrator, Token Saver, Retry, Fallback, Stats, SubAgent, Lifecycle, Turn, Gateway, Workspace Provider.
- WATCH: Custom Router (needs a real `extensionId` plugin), Permission (needs an explicit permission scenario), MCP (needs configured MCP server/tool smoke).
- BLOCKED: `src/evolution` / `src/evolution/auto_evolver.py` was absent in current local/upstream-shaped tree; do not claim it active. Treat only `router.scenarios.evolution` as a routing label unless real source/runtime exists.

## Verification recipe

1. Read remote HEAD with `git ls-remote https://github.com/OpenBMB/PilotDeck.git HEAD`.
2. Confirm local repo/status under `~/.pilotdeck-agi/PilotDeck`.
3. Back up both active configs before editing:
   - `~/.pilotdeck/pilotdeck.yaml`
   - `~/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml`
4. Read schema before adding keys: `src/router/config/schema.ts`, `parseRouterConfig.ts`, `parseAlwaysOnConfig.ts`, `parseCronConfig.ts`.
5. Run `npm run build` after config changes.
6. Restart using the existing wrapper when possible so env/config are loaded:
   - `~/.pilotdeck-agi/state/pilotdeck-agi-overlay/bin/start_pilotdeck_second_agi.sh`
7. Verify:
   - HTTP `/health` returns `{"ok":true}`.
   - WebSocket `/ws` hello succeeds.
   - WS methods `describe_server`, `reload_config`, `list_projects`, `cron_list`, `skill_list`, `describe_project` return success.
8. For Always-On, do not fabricate work cycles. `always_on_apply` returning `cycle_not_found` after a valid projectKey means the runtime is mounted but requires a real workCycleId.
9. Write an evidence report and manifest entry; label WATCH/BLOCKED honestly.

## Pitfalls

- Do not use `/api/config` as PilotDeck gateway evidence; local gateway may only expose `/health` over HTTP and use WS for business methods.
- Do not start built server directly without loading the same env/config as the wrapper; provider env may be missing.
- Do not enable Always-On autonomous triggers by default. Prefer `alwaysOn.enabled=true` with `trigger.enabled=false` until user explicitly authorizes background cycles.
- Do not enable customRouter without a real plugin `extensionId`.
- Do not mark MCP active without an actual configured MCP server and tool smoke.
