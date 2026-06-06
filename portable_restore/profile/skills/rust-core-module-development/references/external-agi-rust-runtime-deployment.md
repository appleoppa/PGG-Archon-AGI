# External AGI/Rust repo runtime deployment pattern

Use when a cloned/generated AGI Rust repository contains a Python Web UI plus a large generated Rust source tree that cannot be safely or quickly linked as-is, but the user requires a real local runnable deployment.

## Pattern

1. Separate three states honestly:
   - Web UI is running.
   - Root Rust crate compiles/runs.
   - Experimental generated modules are fully linked and semantically working.
2. Do not present state 1 as state 2, or state 2 as state 3.
3. First make the root crate deployable:
   - Keep generated `cognitive_core/`, `boundary_gateway/`, etc. as retained source assets if they are structurally broken.
   - Replace or narrow `src/lib.rs` to a stable deployable surface with version, system info, and runtime health structs.
   - Replace `src/main.rs` with a local HTTP runtime (`axum` works well) exposing `/api/health`, `/api/capabilities`, and `/api/chat`.
   - Keep limitations in `/api/capabilities` so future agents do not overclaim.
4. Verify with:
   - `cargo check --all-targets`
   - `cargo test --all-targets`
   - `cargo build --release`
   - run the release binary and `curl` health/chat endpoints.
5. Only then wire Web UI:
   - Bind Flask/Web UI to `127.0.0.1` and `debug=False`.
   - Use a non-conflicting default port such as `5050` on macOS because port `5000` may be occupied by Control Center.
   - Add a `/chat` page and proxy APIs such as `/api/runtime/health` and `/api/chat` forwarding to the Rust runtime.
6. For real model wiring in Rust:
   - Load secrets from env or `~/.hermes/.env`; never print keys.
   - Support explicit env vars (`OMEGA_LLM_PROVIDER`, `OMEGA_LLM_MODEL`, `OMEGA_LLM_MODE`, `OMEGA_LLM_BASE_URL`, `OMEGA_LLM_API_KEY`).
   - For GPT/Claude custom providers in this user's setup, use Responses API (`/v1/responses`) format: `model`, `input`, `instructions`, `max_output_tokens`.
   - Preserve local deterministic fallback but report when real LLM calls fail.
7. Final verification should include both direct Rust call and Web proxy call returning `mode` that proves the real provider path, e.g. `llm:gpt55_5yuantoken:responses`.

## Acceptance language

Acceptable:
- “Root Rust crate is compileable and the local runtime is serving.”
- “Web UI proxies to Rust runtime and the runtime calls a real LLM provider.”
- “Generated experimental modules are retained as source assets but not all linked into the deployable surface.”

Not acceptable:
- “Full AGI is complete” when only runtime/API plumbing is verified.
- “Rust core is deployed” when only Python Web UI is running.
- “LLM is connected” without an actual provider-backed response from the runtime endpoint.
