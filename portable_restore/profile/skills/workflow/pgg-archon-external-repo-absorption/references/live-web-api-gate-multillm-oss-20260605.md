# Live Web/API Gate + Multi-LLM/OSS Absorption Pattern (2026-06-05)

## Trigger

Use after a Rust/PyO3/runtime integration gate has passed, but before claiming a dashboard/API feature is actually live. This pattern is especially relevant for PGG Archon / Hermes Web UI features such as OmniRoute dashboards, control endpoints, Server-Sent Events (SSE), and frontend TypeScript contracts.

## Why this was added

A session reached:

- Rust compile gate: `PASS`
- PyO3 import gate: `PASS`
- focused runtime integration pytest: `36 passed`

But GPT/Claude correctly warned that this still did **not** prove live Web/API behavior. The missing layer was a real temporary web server smoke gate: `/snapshot`, `/control`, `/stream`, auth, negative payloads, SSE framing, and frontend build.

## Required gate sequence

1. **Multi-LLM advisory, not proof**
   - Call available daily/task LLMs for audit suggestions.
   - Call GPT/Claude through the reliable configured route; if direct Responses API fails but Hermes CLI succeeds, record both facts.
   - Agnes/agents should remain `third_party_judge_only` when the user's standing rule applies.
   - Do not let one provider failure block the whole gate; mark that channel `ERROR` and continue.

2. **Read-only open-source learning**
   - Search GitHub / public docs only for patterns.
   - Do not import or execute external repo code unless separately authorized.
   - For SSE/Web API gates, authoritative patterns include:
     - `Content-Type: text/event-stream`
     - frames shaped as `event:` / `data:` blocks ending in a blank line
     - EventSource cannot attach custom headers, so a query token is acceptable only for a narrowly scoped read-only stream; write/control endpoints should keep header token auth
     - control endpoints require side-effect readback after POST
     - frontend contract should be checked by TypeScript build plus live response schema smoke

3. **Temporary live server smoke**
   - Start a local temporary server on a random loopback port.
   - Inject a fixed ephemeral test token via environment, e.g. `HERMES_DASHBOARD_SESSION_TOKEN`.
   - Verify the process is ready by probing a known endpoint.
   - Always terminate/kill the temporary server in a `finally` block.

4. **Positive and negative endpoint checks**
   - Positive:
     - `GET /api/<feature>/snapshot` returns HTTP 200 and expected schema/key types.
     - `POST /api/<feature>/control` returns HTTP 200.
     - A second `GET /snapshot` proves the control side effect was actually persisted/read back.
     - `GET /api/<feature>/stream?...` returns `text/event-stream` and a real `event:`/`data:` chunk.
   - Negative:
     - Missing/invalid token returns 401 for protected endpoints.
     - Invalid control payload returns 400.

5. **Frontend contract build**
   - Run the real frontend build/typecheck command, e.g. `pnpm --dir web build`.
   - If pnpm 11 blocks dependency build scripts with `ERR_PNPM_IGNORED_BUILDS`, the fix is `pnpm --dir web approve-builds --all` followed by a rebuild; record that as a build-environment step, not as application proof.
   - A successful build proves TypeScript/Vite contract integrity, not browser-rendered UX.

6. **Evidence and manifest**
   - Write a `result.json` with:
     - schema/version
     - LLM status by provider, including direct failures and fallback successes
     - OSS/doc sources consulted and patterns absorbed
     - live endpoint check summaries
     - frontend build summary
     - artifact hashes
     - explicit boundary
   - Update `~/.hermes/data/EVOLUTION_MANIFEST.json` and read back the new key before reporting completion.

## Example result boundaries

A truthful `PASS` may say:

> Local compile/integration/live API/frontend gates are verified and multi-LLM/open-source advice was consulted.

It must **not** say:

- browser-rendered UI was visually accepted unless browser/vision/click testing actually happened
- production traffic is routed through Rust unless a live production task route/call proves it
- official external benchmark passed
- AGI level advanced beyond the current evidence
- full AGI / T5 achieved

## Common pitfall

Do not stop at `pytest passed` for Web UI/API work. Unit/integration tests are necessary, but a live Web/API gate needs a real server process, real HTTP requests, auth/negative checks, SSE frame validation, and frontend build verification.
