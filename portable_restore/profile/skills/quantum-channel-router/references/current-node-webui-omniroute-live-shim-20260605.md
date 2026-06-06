# Current Node WebUI OmniRoute live-panel shim (2026-06-05)

## Trigger

Use when PGG OmniRoute / 河图洛书 / quantum router dashboard exists as files or a FastAPI dashboard, but the user expects to see it in the **currently running Hermes WebUI / Desktop Node service**.

## Durable lesson

Do not stop after proving a dashboard HTML/JSON exists. If the user's visible app is the Node `hermes-web-ui` service, verify and integrate against that actual process/port.

## Proven pattern

1. Identify the active WebUI process and port:
   - `ps -axo pid,ppid,command | grep hermes-web-ui`
   - `lsof -nP -iTCP -sTCP:LISTEN | grep node`
   - launchd plist commonly: `~/Library/LaunchAgents/ai.hermes.webui.plist`
2. If the active UI is Node `hermes-web-ui`, a low-risk bridge is:
   - add a static page under `.../hermes-web-ui/dist/client/omniroute.html`;
   - run a localhost-only FastAPI/SSE bridge on `127.0.0.1:<port>`;
   - have the static page call the bridge for `snapshot`, `control`, and `stream`.
3. Keep the bridge local and bounded:
   - bind to `127.0.0.1`;
   - protect REST/SSE with a local dashboard token;
   - add CORS only for localhost origins;
   - allow `OPTIONS` through auth middleware so browser preflight does not break `POST /control`.
4. Verify in the browser, not only via curl:
   - open `http://127.0.0.1:<webui-port>/omniroute.html`;
   - browser console should show `SSE live`;
   - POST manual provider override should change `pageEffective` and `pageMode`;
   - reset to `auto` before final handoff unless the user asked to keep a manual override.
5. Persist runtime control separately from route evidence:
   - manual provider selection is an operator preference, not proof of provider participation;
   - keep a control file such as `~/.hermes/data/omniroute_control.json`;
   - route/call evidence still must come from real task execution.

## Verification checklist

- Static page: `HTTP 200 http://127.0.0.1:<webui-port>/omniroute.html`.
- API service: `launchctl list | grep <label>` and `lsof -iTCP:<bridge-port>`.
- Snapshot: `schema=pgg_omniroute_live_snapshot.v1` and provider list populated.
- SSE: browser shows `SSE live` and first event is `event: snapshot`.
- Control: manual override works, then auto reset works.
- Manifest/readback updated after verification.

## Pitfalls

- A local HTML/JSON file existing is not enough; the user may be looking at a different running UI process.
- Browser `EventSource` cannot send custom headers; use a narrowly scoped query token for the read-only SSE endpoint.
- Browser `fetch(... POST ...)` with custom headers triggers CORS preflight; auth middleware must not 401 `OPTIONS`.
- Do not hard-code secrets from production credentials into static pages. Use a local-only dashboard token and bind the bridge to loopback.
- Do not claim manual override proves provider participation. It only records routing preference/control state.
