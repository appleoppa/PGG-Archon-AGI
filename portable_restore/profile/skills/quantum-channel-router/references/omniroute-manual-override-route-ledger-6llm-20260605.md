# OmniRoute manual override route-decision ledger — 6 LLM reviewed

Date: 2026-06-05
Scope: PGG OmniRoute / HeTuLuoShu current Node WebUI and local quantum router.

## Trigger

Use when the user asks to make OmniRoute manual/auto controls actually affect routing decisions, not just dashboard display.

## Pattern

1. Keep UI control state in `~/.hermes/data/omniroute_control.json`.
2. Add a local decision function in `agent.pgg_archon_quantum_channel_router`:
   - `decide_omniroute_provider(task_type='general', requested_provider='')`
   - Reads Rust dashboard selected provider.
   - Reads manual override from `omniroute_control.json`.
   - Applies priority: explicit request override > manual control > dashboard auto > first available fallback.
   - Writes evidence to `~/.hermes/data/omniroute_route_call_events.jsonl`.
3. Add `recent_omniroute_route_events(limit=20)` for WebUI snapshots.
4. Expose API endpoint:
   - `POST /api/omniroute/decide`
   - response includes `decision` and refreshed snapshot.
5. Add `recent_route_events` to `/api/omniroute/snapshot`.
6. Current Node WebUI shim (`http://127.0.0.1:8648/omniroute.html`) displays:
   - latest selected provider
   - selected_source (`dashboard_auto`, `manual_control`, `request_override`, etc.)
   - manual_override_applied
   - generation_id
   - route event list
   - “记录路由决策” button.

## Verification evidence from implementation

6 LLM review file:
`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/all-llm-omniroute-next-steps-review-20260605.json`

Summary:
- DeepSeek OK
- MiMo OK
- Agnes OK
- MiniMax OK
- gpt5.5 OK
- Claude OK

Route decision verification:

- Direct auto:
  - selected_provider=`mimo`
  - selected_source=`dashboard_auto`
  - manual_override_applied=`false`
- API auto:
  - HTTP 200
  - selected_provider=`mimo`
  - selected_source=`dashboard_auto`
- API manual:
  - manual override `deepseek`
  - HTTP 200
  - selected_provider=`deepseek`
  - selected_source=`manual_control`
  - manual_override_applied=`true`
- Browser current WebUI after click:
  - SSE live
  - mode=auto
  - latest=`mimo | source=dashboard_auto | manual=false`

Screenshot:
`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/current-webui-omniroute-route-ledger-20260605.png`

## Boundary

This is real local route-decision evidence. It still does not prove upstream provider participation until a later execution layer performs an actual provider/API call and links it to the decision/generation id. Do not claim “provider participated” from this ledger alone.
