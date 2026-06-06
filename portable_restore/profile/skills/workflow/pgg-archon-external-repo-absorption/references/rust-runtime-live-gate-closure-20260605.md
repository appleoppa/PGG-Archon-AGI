# Rust/runtime/live gate closure pattern — 2026-06-05

## Trigger

Use when PGG Archon/Hermes work claims that a Rust module, routing surface, Web/API dashboard, or multi-LLM benchmark bridge is “landed” and ready to stage/commit.

## Proven sequence

1. **Formula gate first**
   - Show the `/goal` formula visibly for important AGI/evolution/system tasks.
   - Map the task to 总纲1 dimensions and 总纲2 `Agent_Evolve` stages.
   - State the truth boundary before tool execution.

2. **Rust compile gate**
   - Enumerate all `Cargo.toml` files in scope.
   - Run per-crate `cargo test` and `cargo build --release`.
   - For PyO3/cdylib crates, test Python import by copying/signing the release dylib/so into a temporary import directory and calling at least one exported function.
   - Record env (`cargo`, `rustc`, Python, arch), command, exit code, log path, artifact path, size, and sha256.
   - Do not treat timeout or partial logs as PASS; rerun the specific timed-out build with a longer tracked command.

3. **Runtime integration gate**
   - Run focused pytest proving Python callers and UI/API bridge paths import/use the Rust surfaces.
   - If tests fail due to API contract drift, prefer backward-compatible wrappers and public compatibility functions over mutating tests to match broken code.
   - Keep production paths intact; compatibility wrappers should be labeled and bounded.

4. **Live Web/API gate**
   - Start a temporary local server on a random loopback port with `HERMES_DASHBOARD_SESSION_TOKEN` set.
   - Verify:
     - unauthorized request returns 401;
     - `GET /api/.../snapshot` returns expected schema;
     - `POST /api/.../control` is followed by readback proving the side effect;
     - invalid control payload returns 400;
     - SSE endpoint returns `Content-Type: text/event-stream` and an `event:`/`data:` framed snapshot.
   - Terminate the server and write `result.json`.

5. **Frontend gate**
   - Run TypeScript/Vite build after backend live gate.
   - If pnpm 11 blocks build scripts (`ERR_PNPM_IGNORED_BUILDS`), use project-scoped `pnpm approve-builds --all` only when needed and record the approval as build-environment evidence.
   - Do not automatically stage high-noise lock/workspace files unless package-manager policy requires them.

6. **Multi-LLM + OSS gate**
   - Call daily LLMs and GPT/Claude through real configured providers.
   - If direct Responses calls return 502/403/empty text but Hermes CLI provider calls succeed, record both: direct failure is not hidden, CLI success is valid evidence for that channel.
   - Agnes/agents is third-party judge only when the user policy says so; do not put it into ordinary processing pools. MiMo remains ordinary processing unless separately reclassified.
   - GitHub/MDN/open-source search is read-only by default; absorb patterns, not code, unless explicitly authorized.

7. **Pre-commit gate**
   - Create a bounded review pack for Claude: status, diff stat, critical diffs, untracked summaries, tests, boundaries.
   - Ask Claude for `stage_files` and `hold_files`.
   - Self-review Claude’s result; add missed reproducibility files such as `Cargo.lock` and `proptest-regressions/*.txt` when appropriate.
   - Hold workspace evidence artifacts, build targets, unrelated modified files, and unreviewed generated package files.
   - Run post-stage checks (`git diff --cached --check`, focused pytest, cargo test/build, frontend build, live gate) before commit.

## Pitfalls captured

- A formula rule that is only implicit feels unexecuted to the user; important tasks need visible formula gates.
- A file existing or a server starting is not enough: use import/function smoke, endpoint readback, negative auth, and side-effect verification.
- Tests can pass while encoding the wrong user policy. In this session a remaining diff tried to reserve MiMo as third-party judge and move Agnes into ordinary pools; this violated the user’s rule. Treat provider-role inversions as correctness bugs, not style changes.
- Do not stage `workspace/` evidence artifacts or broad unreviewed leftovers just because a related gate passed.

## Minimal evidence bundle

Store paths to:

- compile gate result JSON;
- runtime integration gate result JSON;
- live Web/API gate result JSON;
- multi-LLM/OSS scout result;
- Claude pre-commit audit;
- post-stage verification log;
- commit SHA if committed.

Boundary: these gates prove local compile/integration/live behavior for the scoped surfaces only. They do not prove production traffic, browser visual acceptance, official external benchmark success, or AGI level advancement.
