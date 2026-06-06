# OmniRoute route-suggest mirror v2.3 — 2026-06-05

## Purpose

Move from mirror-only to route-suggest mode without enforcing routes.

## Behavior

When `~/.hermes/data/omniroute_auto_evidence_bridge.json` has:

```json
{"enabled": true, "mode": "route_suggest"}
```

`AIAgent.run_conversation()` does:

1. Before original conversation: call `decide_omniroute_provider(...)` to get a suggestion.
2. Run the original `agent.conversation_loop.run_conversation(...)` unchanged.
3. After return: write mirror event with `suggested_provider`, `actual_provider`, and `suggestion_matches_actual`.
4. Return original result unchanged.

## Verification observed

Real smoke:

- Prompt: `Reply exactly: PGG_ROUTE_SUGGEST_OK`
- Actual run provider: `custom:gpt55_5yuantoken`, model `gpt-5.5`
- Final answer: `PGG_ROUTE_SUGGEST_OK`
- Route suggestion: `mimo`
- Match: `false`
- WebUI showed suggested vs actual mismatch.

## Boundary

Route-suggest mode does not:

- mutate provider/model
- enforce routing
- make an extra task-solving model call
- change final answer

Next stage is guarded route-enforce mode, which should require explicit authorization and rollback.
