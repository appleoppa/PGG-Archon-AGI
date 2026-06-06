# 9router-style realtime dashboard implementation lessons (2026-06-05)

## Trigger

Use when the user asks whether PGG OmniRoute / 河图洛书 / quantum router can implement 9router-like capability: realtime status panel, unified entry, provider switching, force refresh, dashboard visibility, or route control.

## User workflow correction

The user explicitly objected to prolonged feasibility probing: once 9router realtime-sync structure has been audited and the local OmniRoute / 河图洛书 functions are known to be similar, do not keep asking whether it can be done or produce more comparison prose. Move directly to a low-risk implementation path with verification.

Preferred response shape:

1. State plainly: it can be implemented.
2. Implement the smallest working vertical slice.
3. Verify with real build/API/SSE output.
4. Only then explain remaining integration boundary.

## Minimal safe vertical slice

For Hermes FastAPI dashboard / local router surfaces:

- Backend:
  - `GET /api/omniroute/snapshot` returns current dashboard JSON + provider health + control state.
  - `POST /api/omniroute/control` records `auto` / `manual` mode and selected provider override.
  - `GET /api/omniroute/stream` provides SSE `event: snapshot` with keepalive.
  - Use query-token auth only for the SSE endpoint because browser `EventSource` cannot set custom headers; keep the exception narrowly scoped.
  - Persist control/events under `~/.hermes/data/` as JSON/JSONL for auditability.
- Frontend:
  - Add an `OmniRoute` route and sidebar entry.
  - Show selected/effective provider, route score, order status, provider cards, TTL cache fields, stream state, boundary text.
  - Add controls for Auto router, manual provider selection, force-refresh flag.
- Verification:
  - `python3 -m py_compile hermes_cli/web_server.py`
  - `npm run build` in `web/`
  - REST snapshot returns schema and provider list.
  - REST control manual override then reset auto.
  - SSE emits `event: snapshot` under a fixed test `HERMES_DASHBOARD_SESSION_TOKEN`.

## Important boundary

Hermes may have more than one UI/runtime surface:

- FastAPI dashboard: `hermes_cli/web_server.py` + `hermes_cli/web_dist`.
- Desktop/Node Web UI: e.g. `ai.hermes.webui` running a Node server.

Before claiming the user can see a new page in the currently open app, verify which UI process/port is active. It is valid to say: feature is implemented and verified in the FastAPI dashboard bundle, but the active Desktop/Node Web UI may still need restart or a separate integration bridge.

## Pitfalls

- Do not equate manual provider selection with real provider participation. It records operator preference/control state only; real participation still requires task route/call evidence.
- Do not copy 9router OAuth/free-provider/cookie-bypass logic; absorb the safe class-level sync pattern only.
- Do not drop auditability for pure in-memory state. PGG control/events should land under `~/.hermes/data/`.
- Do not let 9router comparison become an end in itself once the user asks for implementation.
- When testing SSE with FastAPI, avoid TestClient patterns that wait for stream completion; use a temporary uvicorn server plus `curl --max-time` and a fixed test session token.
