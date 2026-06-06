# GitHub Rust/Tauri/Node monorepo local deploy pattern

Use when the user asks to read a GitHub repo and deploy it locally, especially a desktop/Web hybrid repo with Rust core + pnpm/Vite/Tauri.

## Deployment gates

1. **Resolve source repo first**
   - Verify the GitHub owner/repo with `gh repo view` or equivalent authenticated lookup.
   - Clone/update into the workspace deployment area, not Home/Desktop/root.
   - Read repo-level `AGENTS.md`, `README*`, `package.json`, and setup docs before choosing commands.

2. **Install prerequisites by documented versions**
   - Use the repo `packageManager` field for pnpm/Corepack version where possible.
   - Initialize submodules before Tauri/desktop build steps.
   - For Rust/Tauri projects, run both root Rust checks and app-shell checks when the repo separates core and desktop shell.

3. **Prefer layered verification over one giant desktop launch**
   - Rust core: `cargo check` then `cargo build --bin <core-binary>`.
   - JS app: `pnpm --filter <app> compile` and `pnpm --filter <app> build`.
   - Desktop shell: install/ensure the vendored Tauri CLI, then run `cargo check --manifest-path app/src-tauri/Cargo.toml` before attempting GUI launch.
   - Web UI: run Vite on a fixed localhost port and curl the page title/status.
   - Core API: run the core process on a fixed localhost port and curl `/health`.

4. **macOS Tauri/CEF specific fix**
   - Some vendored Tauri/CEF helpers build an `x86_64-apple-darwin` helper even on Apple Silicon.
   - If the build asks for that target, add it to the pinned project toolchain, not only the default toolchain:
     `rustup target add x86_64-apple-darwin --toolchain <pinned-aarch64-toolchain>`.

5. **Health endpoint caveat**
   - If a local core is healthy except the release/update checker fails due to GitHub API rate/403, look for a documented environment flag to disable auto-update for local smoke tests.
   - If the project has an auto-update checker that fails in local deployment, disable it with the project’s documented environment flag and verify `/health` returns 200.
   - Report this as a local smoke-test adjustment, not as a product fix.

## Completion evidence to report

- Source URL, local path, branch and commit.
- Dependency/build checks that passed.
- Running localhost URLs and HTTP status codes.
- Process/listener evidence for core and web ports.
- Git status clean/dirty, and whether any source code was modified.

## Pitfalls

- Do not call a clone a deployment. Deployment requires installed dependencies, built artifacts, running process or executable, and smoke-test output.
- Do not force a GUI/Tauri window launch if layered evidence already proves core + web deploy and the environment is non-interactive; state desktop shell verification level honestly.
- Avoid saving transient missing-binary states as durable rules; save the prerequisite/fix sequence instead.
