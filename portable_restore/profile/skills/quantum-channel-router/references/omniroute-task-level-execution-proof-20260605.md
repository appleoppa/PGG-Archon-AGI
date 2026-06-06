# OmniRoute task-level execution proof — task_id to answer hash

Date: 2026-06-05
Scope: PGG OmniRoute / HeTuLuoShu current Node WebUI and local quantum router.

## Trigger

Use when provider participation proof should be upgraded from a bounded probe to a task-level evidence chain.

## Pattern

Evidence chain:

```text
task_id
  -> route decision
  -> selected provider
  -> real provider API call
  -> answer_preview
  -> answer_sha256
  -> task execution ledger
  -> WebUI display
```

Implementation:

1. `agent.pgg_archon_quantum_channel_router.execute_omniroute_task(task, task_type, requested_provider, timeout)`
   - Creates `task_id`.
   - Calls `execute_omniroute_provider_call()`.
   - Records `task_sha256`, `answer_sha256`, provider/model/http/latency/visible chars.
   - Writes `~/.hermes/data/omniroute_task_execution_events.jsonl`.
2. `recent_omniroute_task_execution_events(limit=20)` returns tail events.
3. FastAPI:
   - `POST /api/omniroute/task`
   - snapshot includes `recent_task_events`.
4. Current Node WebUI shim:
   - `http://127.0.0.1:8648/omniroute.html`
   - Button: `真实任务执行`
   - Panel: `Task-level proof`.

## Verification evidence

Direct task:

```text
task_id=61c7b88c644b3594
provider=mimo
success=true
http_status=200
visible_chars=11
answer_preview=PGG_TASK_OK
answer_sha256=c1bf00ef...
```

API task:

```text
task_id=a90f6c80a3e5b4b4
provider=mimo
success=true
http_status=200
visible_chars=11
answer_preview=PGG_TASK_OK
```

Browser button:

```text
SSE live
taskEventCount=3 tasks
latest=875de20106fd4452 provider=mimo success=true http=200 chars=11 answer=PGG_TASK_OK
```

Screenshot:
`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/current-webui-omniroute-task-level-proof-20260605.png`

Manifest key:
`latest_pgg_omniroute_task_level_execution_proof_20260605`

## Boundary

This proves task-level provider participation and answer hashing only for the bounded task tied to the recorded `task_id`. It is not a benchmark, legal correctness proof, full AGI evidence, or proof for unrelated tasks unless they have their own linked task/decision/provider-call records.
