# APEX-MEM local Rust service deployment pattern

Use when asked to read/deploy the user's APEX-MEM GitHub repository or a similar Rust memory-retrieval service locally.

## Durable workflow

1. Discover the GitHub repo with `gh repo list <owner> --json nameWithOwner,url,visibility,isPrivate`; do not assume the clone already exists.
2. Clone/update under the governed workspace path, e.g. `~/.hermes/workspace/github/<owner>/<repo>`; keep runtime data under `~/.hermes/workspace/runtime/<service>` and deploy binaries under `~/.hermes/workspace/bin/`.
3. Inspect README/Cargo.toml and build with `cargo build --release`.
4. Run `cargo test` before claiming deployment. Capture totals from unit, integration, compat, and doc tests.
5. Copy the release binary to a stable deploy path and record `--version` plus SHA-256.
6. Run CLI smoke tests before starting a service: ingest → search → stats → dream/self-diagnosis.
7. For Axum/Clap-style CLIs, global options often must precede the subcommand. Example: `apex-mem --bind 127.0.0.1:8765 serve`, not `apex-mem serve --bind ...`.
8. Start the service and verify all advertised surfaces, not just process existence:
   - REST: `/health`, `/v1/stats`, `/v1/search`
   - MCP: `/mcp/tools`, `/mcp/rpc tools/list`, one `tools/call`
   - Local port: `127.0.0.1:<port>` is LISTEN
9. If the user asked for local deployment, a user LaunchAgent is acceptable when low-risk and reversible. Use a plist under `~/Library/LaunchAgents/`, logs under the workspace runtime directory, then verify with `launchctl print`, `lsof`, and HTTP probes.
10. Write a short deployment report under a governed reports directory with source path, binary path, runtime path, service URL, test totals, live endpoints, hashes, and known boundaries.

## Evidence standard

Deployment means: source cloned + binary built + tests pass + CLI smoke passes + live service probes pass + persistence/auto-start configured when requested. File existence or a running process alone is not enough.

## Boundary language

State the active embedding provider honestly. For APEX-MEM default local deployment, `hashing-v1` is a deterministic local embedder, not a remote OpenAI/Candle semantic model. Localhost binding means the service is not exposed externally.
