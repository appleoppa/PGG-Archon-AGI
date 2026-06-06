# OmniRoute main task execution chain v2 — 2026-06-05

## Capability

Adds a bounded main-task API path separate from cockpit probes:

`task_id -> route decision -> provider participation -> answer hash -> task evidence package -> WebUI tracking`

## Endpoint

```http
POST /api/omniroute/execute
```

Body:

```json
{
  "task_type": "dashboard_main_task",
  "task": "请只回答：PGG_MAIN_TASK_OK",
  "requested_provider": "",
  "timeout": 60
}
```

## Evidence package

Each successful or failed task writes:

- `~/.hermes/workspace/github_absorption/9router/analysis/evidence/omniroute-task-evidence-{task_id}.json`
- `~/.hermes/workspace/github_absorption/9router/analysis/evidence/latest-omniroute-task-evidence.json`

Snapshot adds `task_evidence_package` with latest task/provider/success/hash.

## Verification used

```bash
curl -sS -X POST http://127.0.0.1:9197/api/omniroute/execute \
  -H 'Content-Type: application/json' \
  -H 'X-Hermes-Session-Token: <LOCAL_SESSION_TOKEN_PLACEHOLDER>' \
  -d '{"task_type":"api_main_task_chain_probe","task":"请只回答：PGG_MAIN_TASK_OK","requested_provider":"","timeout":60}'
```

Observed bounded proof:

- `task_id=44f42433b6abf5a9`
- selected provider: `mimo`
- `http_status=200`
- answer: `PGG_MAIN_TASK_OK`
- evidence package exists and read back.

## Boundary

This proves the OmniRoute dashboard/API path can execute a bounded main task with route/provider/evidence chain. It is not yet a transparent replacement for Hermes core conversation routing and is not benchmark/legal-correctness/full-AGI evidence.
