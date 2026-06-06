# OmniRoute provider participation ledger — route decision to real API call

Date: 2026-06-05
Scope: PGG OmniRoute / HeTuLuoShu current Node WebUI and local quantum router.

## Trigger

Use when the user says "继续" after manual override route-decision ledger, or asks to prove that a selected provider actually participated.

## Pattern

1. Decision stage:
   - `decide_omniroute_provider(task_type, requested_provider)` chooses the provider from explicit request > manual control > dashboard auto > fallback.
   - Writes `omniroute_route_call_events.jsonl`.
2. Participation stage:
   - `execute_omniroute_provider_call(prompt, task_type, requested_provider, timeout)` calls `decide_omniroute_provider()` first.
   - It then finds the selected provider in the verified `PROVIDERS` registry from `agent.pgg_archon_external_benchmark_provider_run`.
   - Calls the selected provider with `call_provider()`.
   - Writes `~/.hermes/data/omniroute_provider_call_events.jsonl`.
3. API:
   - `POST /api/omniroute/call` executes the participation probe and returns `{ok,result,snapshot}`.
   - Snapshot includes `recent_provider_call_events`.
4. Current Node WebUI:
   - `http://127.0.0.1:8648/omniroute.html` shows Provider participation proof.
   - Button: `真实 Provider 调用`.

## Verification evidence from implementation

Direct call:

```text
provider=mimo
model=mimo-v2.5-pro
api_mode=chat
participated=true
http_status=200
visible_chars=12
elapsed_sec=8.407
parsed_preview=PGG_ROUTE_OK
```

API call:

```text
POST /api/omniroute/call
HTTP 200
provider=mimo
participated=true
http_status=200
visible_chars=12
elapsed_sec=7.836
parsed_preview=PGG_ROUTE_OK
```

Browser button:

```text
SSE live
providerCallCount=3 calls
latest=mimo mimo-v2.5-pro participated=true http=200 chars=12 elapsed=5.845s preview=PGG_ROUTE_OK
```

Screenshot:
`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/current-webui-omniroute-provider-participation-20260605.png`

Manifest key:
`latest_pgg_omniroute_provider_participation_ledger_20260605`

## Boundary

This proves selected-provider participation for this bounded probe only. It is not a benchmark, not legal correctness, not full AGI evidence, and not proof of provider participation in unrelated tasks unless a later task links its decision/generation id to the provider-call record.
