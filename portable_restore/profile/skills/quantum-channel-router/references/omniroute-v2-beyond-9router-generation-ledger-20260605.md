# OmniRoute v2 beyond-9router pattern — generation + ledger + true refresh

Date: 2026-06-05
Scope: PGG OmniRoute / HeTuLuoShu realtime dashboard for the current Node Hermes WebUI.

## Trigger

Use when improving PGG OmniRoute after 9router absorption, especially when the user asks to optimize/surpass 9router rather than merely show a static panel.

## What was learned

9router useful patterns:

- Frontend TTL store.
- Dynamic/no-store API.
- EventEmitter pending/update split.
- SSE initial full snapshot + lightweight incremental updates + keepalive.
- Provider test-batch grouping.

Open-source observability/gateway patterns scanned:

- BerriAI/litellm: gateway/proxy, dashboard/spend.
- Helicone/helicone: gateway/routing/fallback/observability/tracing/metrics/cost.
- langfuse/langfuse: observability/tracing.
- Portkey-AI/gateway: gateway/routing/fallback/observability.
- openlit/openlit: observability/dashboard/metrics/health/cost.

## Local v2 enhancements

PGG OmniRoute can locally exceed 9router in credibility/auditability for this bounded use case by adding:

1. `pgg_omniroute_live_snapshot.v2`.
2. `generation_id`: SHA256-derived consistency hash from dashboard/health/control/events file signatures and epochs.
3. `consistency_status`: `consistent` vs `mixed_generation`.
4. `recent_events` in every snapshot.
5. True force refresh: `POST /api/omniroute/control {force_refresh:true}` sets `PGG_OMNIROUTE_HEALTH_FORCE_REFRESH=1`, calls `_run_omniroute_dashboard()`, triggers provider health `refresh_forced`, regenerates Rust dashboard, and records `force_refresh_requested/started/finished/error`.
6. Current Node WebUI shim at `http://127.0.0.1:8648/omniroute.html` displays generation, consistency, events, refresh result, provider cards, TTL health, and manual/auto override.

## Verification evidence from implementation

- API snapshot: `schema=pgg_omniroute_live_snapshot.v2`.
- Generation: e.g. `generation_id=19990b9aa1038b9e`.
- Consistency: `consistent`.
- Force refresh: `refresh_result.status=present`, `elapsed_sec=8.843`, `provider_health_cache_status=refresh_forced`.
- Browser: `SSE live`, schema v2, event ledger visible, no page error.
- Claude review: HTTP 200, visible output, verdict PASS for bounded credibility/auditability improvement; not a full product-wide superiority claim.

## Boundaries

- This is not a full claim that PGG is better than 9router as an entire gateway/product.
- Manual override is an operator preference in `omniroute_control.json`; it does not prove provider task participation.
- Realtime dashboard visibility is not AGI capability, benchmark performance, or legal correctness.
- Keep the API bound to `127.0.0.1`; do not expose the local dashboard token to arbitrary networks.

## Files

- Backend: `/Users/appleoppa/.hermes/hermes-agent/hermes_cli/web_server.py`.
- Current Node WebUI page: `/Users/appleoppa/.npm-global/lib/node_modules/hermes-web-ui/dist/client/omniroute.html`.
- Launchd API service: `/Users/appleoppa/Library/LaunchAgents/ai.hermes.omniroute-dashboard-api.plist`.
- Open-source scan: `/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/open-source-gateway-observability-scan-20260605.json`.
- Claude audit: `/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/claude-omniroute-beyond-9router-audit-20260605.json`.
