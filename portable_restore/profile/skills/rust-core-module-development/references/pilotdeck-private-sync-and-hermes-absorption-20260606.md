# PilotDeck private sync + Hermes evolution absorption — 2026-06-06

## When to use

Use when the user asks to make local PilotDeck portable across machines, sync PilotDeck source to a private GitHub repo, or let PilotDeck absorb Hermes Agent/PGG evolution content with Rust.

## Durable workflow

1. **Do not push the shallow OpenBMB checkout directly.** The local PilotDeck checkout may be shallow and direct push can fail with missing objects. Use a clean snapshot mirror instead.
2. **Private repo target:** `https://github.com/appleoppa/PilotDeck-apple-sync`.
3. **Source mirror script:** `scripts/apple-sync-to-github.mjs` in local PilotDeck.
   - Manual sync: `npm run apple:sync`
   - Hook install: `npm run apple:sync:install-hook`
   - Installed hooks: `post-commit`, `post-merge`, `post-rewrite`
4. **Snapshot exclusions are mandatory:** `.env`, `home/.pilotdeck/.env`, `.pilotdeck/`, `auth.db`, `node_modules/`, `ui/node_modules/`, `dist/`, `target/`, telemetry/memory sqlite state.
5. **Secret scan before push:** staged mirror changes must be scanned for real token/private-key patterns before commit/push.
6. **Git LFS boundary:** upstream OpenBMB LFS objects may be unavailable due to LFS budget. The private mirror is a code/deployment snapshot; `.gitattributes` LFS filters are neutralized so clone/deploy is not blocked. Media/icon files may remain pointer placeholders.

## Hermes → PilotDeck Rust absorption

PilotDeck now has a Rust bridge under:

```text
rust/apple_evolution_bridge/
```

Run and verify:

```bash
cd /Users/appleoppa/.pilotdeck-agi/PilotDeck/rust/apple_evolution_bridge
/Users/appleoppa/.cargo/bin/cargo fmt --all
/Users/appleoppa/.cargo/bin/cargo test --locked
/Users/appleoppa/.cargo/bin/cargo build --release --locked

cd /Users/appleoppa/.pilotdeck-agi/PilotDeck
npm run apple:absorb-hermes
```

Outputs:

```text
docs/apple-sync/evolution/hermes_evolution_absorption.json
docs/apple-sync/evolution/hermes_evolution_absorption.md
```

Expected evidence from the verified run:

```text
status=PASS
absorbed_count=56
watch_count=2
blocked_count=0
audit_hash=sha256:de89f08d82fa9dc9de616a1cc61eb593bcf6c851d387e1dc02b8b11bb67da905
```

## Key pitfalls fixed

- `git archive HEAD` can trigger LFS filters and fail if `git-lfs` is unavailable or upstream LFS budget is exhausted. Prefer file-level clean snapshot copy via `git ls-files` plus exclusions.
- New Rust crates need `Cargo.lock` generated once before `cargo test --locked` works.
- Historical Hermes manifest entries containing `BLOCKED`/`ERROR` are lessons to absorb as `WATCH`, not failures of the current PilotDeck absorption bridge.
- Auto-sync must exclude Rust `target/`; an earlier hook run pushed build artifacts, then the script was fixed and the remote `target/` directory was deleted. Verify with GitHub API returning 404 for `rust/apple_evolution_bridge/target`.
- Do not call a sync complete until private GitHub remote files are read back with `gh api` or `git ls-remote`.

## Boundary wording

This workflow makes local PilotDeck source and governance overlays portable via private GitHub and lets PilotDeck absorb Hermes evolution evidence as Rust-generated governance artifacts. It does not copy secrets, local auth DBs, provider accounts, node_modules, build artifacts, Hermes core scheduler/security boundaries, or prove AGI/external benchmark success.
