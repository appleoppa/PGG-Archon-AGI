# OmniRoute auto-evidence bridge v2.1 — 2026-06-05

## Purpose

Low-risk bridge that lets ordinary tasks be submitted into the OmniRoute evidence ledger without modifying Hermes core PTY/TUI/conversation loop.

## Endpoints

Configure:

```http
POST /api/omniroute/bridge/config
```

Body:

```json
{
  "enabled": true,
  "mode": "manual_submit",
  "requested_provider": "",
  "timeout": 60
}
```

Submit task:

```http
POST /api/omniroute/bridge/submit
```

Body:

```json
{
  "task": "请只回答：PGG_BRIDGE_OK",
  "source": "api_auto_evidence_bridge_probe"
}
```

## Artifacts

- Bridge config: `~/.hermes/data/omniroute_auto_evidence_bridge.json`
- Task evidence package: `~/.hermes/workspace/github_absorption/9router/analysis/evidence/omniroute-task-evidence-{task_id}.json`
- Latest task evidence: `~/.hermes/workspace/github_absorption/9router/analysis/evidence/latest-omniroute-task-evidence.json`

## Verification observed

- `enabled=true`, `mode=manual_submit`
- task `请只回答：PGG_BRIDGE_OK`
- selected provider `mimo`
- HTTP 200
- answer `PGG_BRIDGE_OK`
- task_id `734676ae75b6bd66`
- evidence package exists and read back.

## Boundary

This is not a transparent hook into Hermes core conversation routing. The current Desktop/WebUI is primarily PTY/TUI embedded; hard-hooking that loop is higher-risk and should be separate. This bridge is intentionally reversible and explicit.
