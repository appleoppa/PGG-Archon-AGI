# nanoGPT-claw local Rust sidecar deployment note

Session-derived reusable pattern for deploying a Rust sidecar CLI/daemon locally on macOS.

## Problem pattern

A sidecar repository may claim CI/build success, but a fresh local deployment can still fail when runtime-only code paths call missing config constructors. In this case `daemon` initialization called `GatewayConfig::from_env()` while `GatewayConfig` only implemented `Default`.

## Durable fix pattern

1. Run `cargo test` before assuming the release binary is usable.
2. If daemon startup depends on env-backed gateway config, implement a small `from_env()` builder near the config type rather than wiring secrets directly into the daemon.
3. Safe default: all external gateways stay disabled unless explicitly enabled, e.g. `FEISHU_ENABLED=true` / `GITHUB_ENABLED=true`.
4. Read secrets only through env vars and never print them.
5. Preserve compatibility with alternate env names where the repo already uses both forms, e.g. `FEISHU_VERIFY_TOKEN` and `FEISHU_VERIFICATION_TOKEN`.
6. After build, clean generated runtime artifacts from the git worktree (`target/.rustc_info.json`, local sqlite DBs) before committing.

## Verification checklist

- `cargo test` passes.
- `cargo build --release` passes.
- Copy release binary to the deployment path.
- `chmod 755` and macOS ad-hoc codesign the copied binary.
- Start daemon in a tracked background process.
- Verify PID file, `kill -0 <pid>`, CLI `status`, and one business command such as `skill run status`.
- Commit only the minimal source fix required for deployment; do not include `target/` changes or runtime DBs.

## Diff hygiene pitfall

Running `cargo fmt` / `rustfmt` on an inherited unformatted repository can create huge unrelated diffs. Prefer formatting/checking only the file you changed, then restore unrelated files before commit.
