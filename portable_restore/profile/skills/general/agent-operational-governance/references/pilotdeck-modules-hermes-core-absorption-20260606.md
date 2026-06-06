# PilotDeck 14/15 Hidden Modules → Hermes/PGG Core Absorption（2026-06-06）

## Source evidence

Remote repo: `https://github.com/OpenBMB/PilotDeck`.
Local deployment: `/Users/appleoppa/.pilotdeck-agi/PilotDeck`.
Evidence reports:

- `/Users/appleoppa/.hermes/workspace/治理/pilotdeck-hidden15-activation/pilotdeck-hidden15-evidence-20260605-234637.md`
- `/Users/appleoppa/.hermes/workspace/治理/pilotdeck-hidden15-activation/pilotdeck-watch3-resolved-20260606-000301.md`

Final PilotDeck evidence state: `14 PASS / 0 WATCH / 1 BLOCKED`.
The blocked item is `src/evolution`, because current OpenBMB/PilotDeck tree has no such path. Do not claim it exists.

## Absorption boundary

This is not a source-code transplant from PilotDeck into Hermes. PilotDeck remains an independent runtime. Hermes/PGG absorbs the reusable architecture patterns, gates, and evidence discipline:

1. source exists
2. config enabled
3. runtime reachable
4. protocol smoke passes
5. evidence-chain written
6. manifest state updated

Never collapse these into one “activated” claim.

## 14 absorbed module patterns

### 1. Always-On Discovery → Hermes bounded background trigger pattern

Absorb as: background/autonomous systems must have explicit trigger gates, daily budget, cooldown, project scope, workspace isolation, and manual/apply smoke.

Hermes rule: autonomous trigger can stay off while manual/apply runtime is PASS. Do not claim full always-on execution unless a valid work cycle runs.

### 2. Router Orchestrator → Hermes orchestrator/subagent dispatch pattern

Absorb as: complex tasks should be classified and routed to orchestrator mode with a small tool allowlist. Main orchestrator plans/delegates; workers execute.

Hermes mapping: `delegate_task`, subagent-driven development, and apple-hub-orchestrator should prefer scoped allowed tools and explicit final verification.

### 3. Token Saver → Hermes token hygiene and tiered-routing pattern

Absorb as: classify tasks into simple / medium / complex / reasoning before loading big skills or spawning heavy agents.

Hermes mapping: token-hygiene + full-toolcall-integration; use small context and targeted reads before broad scans.

### 4. Router Retry → Hermes bounded retry pattern

Absorb as: retry only transient/zero-usage failures with max attempts and backoff; do not retry semantic failures blindly.

Hermes mapping: provider/gateway calls should record retry reason and stop after bounded attempts.

### 5. Router Fallback → Hermes provider fallback discipline

Absorb as: fallback chain must be explicit by scenario; tool-bearing requests must not fall to chat-only models.

Hermes mapping: model routing must preserve tool capability and API mode; GPT/Claude Responses API cannot be downgraded to chat completions.

### 6. Router Stats → Hermes cost/usage evidence pattern

Absorb as: collect usage/cost stats and saved-cost baselines when routing decisions matter.

Hermes mapping: model/router repair reports should include usage/cost consequences when available.

### 7. Custom Router → Hermes safe hook pattern

Absorb as: custom router hooks must be narrow, tagged, reversible and smoke-tested. PilotDeck smoke router only acts on `[pilotdeck-custom-router-smoke]`.

Hermes mapping: no broad monkeypatch/router override without explicit tags, backups, build, and route-decision smoke.

### 8. SubAgent System → Hermes subagent verification pattern

Absorb as: subagents need inherited context boundaries, task-specific prompts, and parent-side verification.

Hermes mapping: delegate_task results are self-reports; parent must verify file/URL/status handles before claiming completion.

### 9. Lifecycle Hooks → Hermes config-change/hot-reload pattern

Absorb as: config reload should emit changed paths and invalidate runtimes. A reload event is evidence only when read back.

Hermes mapping: after config edits, verify changed path / service reload / health / actual protocol smoke.

### 10. Permission → Hermes non-destructive permission rule pattern

Absorb as: permission systems should have allow/deny rules, normalized patterns, and readback. PilotDeck smoke used read/search allow + dangerous bash deny.

Hermes mapping: high-risk shell, delete, credentials, scheduler/security boundary edits require explicit scope; read-only smoke can prove rule loading without destructive action.

### 11. MCP → Hermes local tool bridge pattern

Absorb as: MCP/tool bridges are PASS only when config parses, runtime is ready, and tools are listed. A static config alone is WATCH.

Hermes mapping: any MCP or sidecar bridge needs config parse + runtime status + listTools/call smoke.

### 12. Turn Management → Hermes turn-state discipline

Absorb as: agent turn state is a first-class runtime object; active turns, sessions and event replay must be distinguished from historical logs.

Hermes mapping: when UI sessions fail, inspect current run/session state, not only historical messages.

### 13. Gateway → Hermes protocol smoke pattern

Absorb as: HTTP health is not enough; real protocol smoke must use the correct transport (`/ws` for PilotDeck) and method calls.

Hermes mapping: for Web UI/bridge/gateway, verify actual protocol request/response, not just port/listener.

### 14. Workspace Provider → Hermes isolated workspace pattern

Absorb as: autonomous/agent work should use isolated worktrees/snapshots and retained artifacts for inspection.

Hermes mapping: PGG/Hermes artifacts go under `~/.hermes/workspace/`; external independent agents keep separate hidden homes.

## Non-absorbed blocked item

`Evolution src/evolution` is not absorbed as a concrete PilotDeck module because it does not exist in the current repo. Hermes already has its own PGG/Rust evolution mechanisms. Treat PilotDeck “evolution” only as a scenario route/config concept unless the upstream repo later adds a real `src/evolution` module and it is verified.

## Hermes execution gate after absorption

For independent-agent or router-feature activation:

```text
SourceExists → ConfigEnabled → Build/Test → RuntimeHealth → ProtocolSmoke → EvidenceReport → ManifestUpdate
```

Completion language:

- PASS: source/config/runtime/protocol evidence all read back.
- WATCH: source exists but missing config, runtime, plugin, or smoke.
- BLOCKED: source path / dependency / protocol does not exist.

## Current PilotDeck final state evidence

- `npm run build`: PASS.
- Gateway `/health`: `{"ok":true}`.
- Gateway WS `/ws`: hello / describe_server / reload_config / list_projects / cron_list / skill_list / describe_project PASS.
- Custom Router: `pilotdeck-smoke-router` resolved tagged smoke request from `custom`.
- Permission: `permissions.json` normalized allow/deny rules; `skipPermissions=false`.
- MCP: local read-only stdio server ready; listed `pilotdeck_smoke_status`.

## Boundary

This absorption improves Hermes orchestration/governance patterns. It does not mean Hermes now runs PilotDeck internals, does not merge runtimes, does not modify Hermes scheduler/security boundary, and does not prove external AGI capability.

## Rust compiled Hermes landing（2026-06-06）

PilotDeck-derived module patterns are now also represented as a compiled Hermes Rust/PyO3 module:

- crate: `/Users/appleoppa/.hermes/hermes-agent/rust_modules/hermes_pgg_pilotdeck`
- Python module: `hermes_pgg_pilotdeck`
- config: `/Users/appleoppa/.hermes/workspace/pgg-archon-governance/pilotdeck_absorbed_patterns_config.json`
- result: `/Users/appleoppa/.hermes/workspace/pgg-archon-governance/pilotdeck_rust_absorption_result.json`
- state: `PASS=14 / WATCH=0 / BLOCKED=1`
- gate: `SourceExists → ConfigEnabled → BuildTest → RuntimeHealth → ProtocolSmoke → EvidenceReport → ManifestUpdate`

Boundary: additive evaluator/config generator only; PilotDeck remains independent; no scheduler/security mutation.
