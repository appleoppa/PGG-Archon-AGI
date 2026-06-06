# Rust Generated Runtime Deploy Pattern

Use when a cloned/generated AGI/Rust repository contains many ambitious modules but fails `cargo check`, while the user requires a local runnable deployment.

## Durable lesson

Do not call a repository "deployed" just because Web UI starts or files exist. A runnable deployment needs at least one compiled Rust entrypoint, a live process, and verified health/interaction endpoints.

When generated source trees are too broken to fully link in one pass, use a truthful deployable surface pattern:

1. **Keep experimental assets, narrow the compiled surface**
   - Retain generated directories such as `cognitive_core/`, `boundary_gateway/`, pipeline scripts, and Web UI as source assets.
   - Make the root crate expose a small, stable runtime API (`VERSION`, `system_info`, `RuntimeHealth`) instead of importing every broken module.
   - Say clearly that retained assets are not all linked into the deployable crate.

2. **Make root Rust actually build**
   - Run `cargo check --all-targets` until it passes.
   - Run `cargo test --all-targets` and require explicit pass/fail counts.
   - Run `cargo build --release` and verify the binary path with `file` or equivalent.
   - If examples reference nonexistent modules, rewrite examples to the current public API rather than deleting evidence silently.

3. **Provide an interaction runtime**
   - Add a small HTTP runtime with `/api/health`, `/api/capabilities`, and `/api/chat`.
   - Bind to `127.0.0.1` by default.
   - Response text must identify limitations: deployability/interaction plumbing is not proof of autonomous AGI cognition.

4. **Bridge Web UI to Runtime**
   - Avoid macOS port `5000` if occupied by system services; make Web UI host/port configurable and default to a safer local port such as `5050`.
   - Add Web UI proxy endpoints: `/api/runtime/health` and `/api/chat` forwarding to `OMEGA_RUNTIME_URL`.
   - Add a user-visible `/chat` page for actual interaction.

5. **Verify live deployment**
   - Check listening ports for both Web UI and Rust runtime.
   - Curl runtime `/api/health` and `/api/chat`.
   - Curl Web UI proxy `/api/runtime/health` and `/api/chat`.
   - Only then say "local runnable deployment completed".

## Report wording

Use a precise boundary:

- Correct: "Root Rust crate builds/tests/runs; Web UI forwards to Rust runtime; experimental generated modules are retained as assets and not all linked."
- Incorrect: "Full AGI core is deployed" unless the full core is linked, tested, and executing.

## Commit discipline

Commit only the deployment-surface files changed in the current round: crate manifests, root `src/lib.rs`, root `src/main.rs`, Web UI proxy/page files, and directly repaired syntax issues. Do not accidentally add build artifacts or unrelated generated files.
