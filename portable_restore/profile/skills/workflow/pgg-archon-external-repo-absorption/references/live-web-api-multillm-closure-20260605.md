# Live Web/API + Multi-LLM Closure Pattern — 2026-06-05

## Trigger

Use when a Rust/runtime integration gate has passed but the remaining gap is whether a Web/API/UI surface is live, authenticated, streaming correctly, and frontend-compatible. Especially relevant when the user asks to call all LLMs and learn from GitHub/open-source without faking completion.

## Proven sequence

1. **Formula gate first**
   - Map to 总纲1 dimensions: real-world landing, autonomous action, knowledge evolution, truth governance.
   - Map to 总纲2: `LDR(K) → GapDetect → OpenSourceLearn → MultiLLM → CodeSelfFix → LiveVerify → KnowledgeSettle`.
   - State boundary before acting: local gate only, not official benchmark/full AGI.

2. **LLM collaboration**
   - Call available daily providers normally.
   - GPT/Claude should use configured Hermes provider/CLI path when direct Responses HTTP is flaky; record direct failures separately.
   - Agnes is third-party judge only when user has that policy.
   - LLM outputs are advisory; they do not prove live endpoints.

3. **Open-source learning**
   - Prefer authoritative docs for protocol facts, e.g. MDN EventSource/SSE.
   - GitHub search is read-only reference/radar; noisy hits do not count as absorption.
   - Do not import/execute external code without separate authorization.

4. **Live Web/API gate**
   - Start temporary loopback server on a free port with a fixed test session token.
   - Positive checks:
     - `GET /api/.../snapshot` returns expected schema/typed fields.
     - `POST /api/.../control` returns 200 and a subsequent snapshot proves side-effect readback.
     - `GET /api/.../stream?token=...` returns `Content-Type: text/event-stream` and an `event:`/`data:` chunk.
   - Negative checks:
     - missing/invalid token returns 401 on protected JSON endpoint.
     - invalid control payload returns 400.
   - Always terminate the temporary server and save JSON evidence.

5. **Frontend contract gate**
   - Run the project’s type/build command (`tsc`, Vite, etc.).
   - If package manager blocks dependency build scripts (e.g. pnpm approve-builds), apply the minimal explicit approval and report it as build-environment setup.
   - Build success is type/bundle evidence, not browser visual QA.

6. **Commit discipline**
   - Before staging, call Claude/GPT on a bounded review pack if user asks for joint review.
   - Stage only scoped files; hold workspace evidence, high-noise lockfiles unless manifest/package changes justify them, unrelated modified files, and unreviewed crates.
   - If a Rust crate is staged, include `Cargo.lock` when it is an application/binary crate or needed for reproducible gate results; include proptest regression seeds when generated and relevant.
   - Run `git diff --cached --check`, focused pytest, crate `cargo test/build`, frontend build, and live API gate after staging.

## Evidence fields to record

- LLM provider/model/status/exit path, including direct failures and fallback CLI success.
- OSS/docs consulted and absorbed patterns.
- Live server PID/port/log path and endpoint results.
- Frontend build command and output summary.
- Test commands and pass counts.
- Manifest key/path and SHA-256 artifact hashes.
- Explicit boundary: no browser visual QA, no production-traffic proof, no official benchmark/full AGI claim.

## Pitfalls

- Do not call a focused pytest pass “live Web/API pass”; start the server and curl/urllib the endpoints.
- EventSource cannot set custom headers; token query may be acceptable only for a narrow read-only stream endpoint. Keep writes on header token auth.
- `POST /control` success is insufficient; always read back snapshot state.
- Package-manager generated lock/workspace files are not automatically stageable; decide with package policy and diff scope.
- Workspace evidence artifacts should generally remain untracked.
