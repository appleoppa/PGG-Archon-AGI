# OmniRoute route-enforce canary v3.6 — 2026-06-06

## Status

`PASS_DEFAULT_OFF_EXACT_GENERAL_CANARY_LEGAL_DENY`

## Implemented

- `execute_route_enforce_canary()`
- API: `POST /api/omniroute/enforce/execute-canary`
- default-off temporary canary enable + finally rollback
- exact/general GPT55 same-class execution only
- legal/audit/AGI deny before provider call

## Exact canary proof

```json
{
  "api_ok": true,
  "success": true,
  "executed": true,
  "http": 200,
  "answer": "PGG_V36_API_EXACT_OK"
}
```

## Legal deny proof

```json
{
  "api_ok": false,
  "success": false,
  "executed": false,
  "error": "route-enforce canary denied by guard",
  "reasons": [
    "intent_denied:chinese_legal",
    "intent_not_allowed:chinese_legal",
    "route_class_mismatch:deepseek->gpt"
  ]
}
```

Combined evidence JSON:

`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/omniroute-v36-route-enforce-canary-dual-proof.json`

## Boundary

This is still a default-off canary, not global route-enforce. It temporarily enables canary mode for one bounded exact/general task, executes GPT55 same-class proof, then rolls back. Legal/audit/AGI remain denied.
