# Rust-native fused watcher manifest update note

Session-derived note for the Rust-native PGG background evolution path.

## What changed

- Active launchd is `ai.hermes.evol-watcher`.
- It runs the Rust binary `~/.hermes/apex-evolution-engine/target/release/apex13 fused-watch`.
- Legacy `com.appleoppa.apex-god.ars` and `com.appleoppa.apex-god.autoloop` are disabled compatibility labels only.
- `EVOLUTION_MANIFEST.json` now contains a `rust_native_background_evolution` entry.

## Verified evidence pattern

Use all of these before calling the migration complete:

- `launchctl list | egrep 'ai.hermes.evol-watcher|com.appleoppa.apex-god'`
- `ps -p <pid> -o pid,ppid,command`
- `grep '"_background_cycle"' ~/.hermes/logs/evol_watcher.log | tail`
- `python - <<'PY'` read back `~/.hermes/data/pgg-background-evolution/status.json`
- Read back `~/.hermes/data/EVOLUTION_MANIFEST.json`

## Manifest updater lessons

- Do not depend on removed `se20` entrypoints for the Rust-native path.
- Generate a manifest entry from live launchd/process/log/status evidence.
- Back up the existing manifest before writing.
- Treat `legacy_labels.disabled=true` as a compatibility fact, not a failure.

## Memory drift repair pattern

When the memory store refuses an update because the file drifted or exceeded quota:

1. Back up the current `MEMORY.md`.
2. Rewrite it as a compact `§`-delimited list.
3. Keep only durable facts: user preferences, current runtime facts, stable paths, and current migration state.
4. Then write the new memory entry.

## Current artifact paths

- Manifest: `/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json`
- Status: `/Users/appleoppa/.hermes/data/pgg-background-evolution/status.json`
- Ledger: `/Users/appleoppa/.hermes/data/pgg-background-evolution/ledger.jsonl`
- Log: `/Users/appleoppa/.hermes/logs/evol_watcher.log`
- Report: `/Users/appleoppa/.hermes/workspace/治理/pgg-background-evolution-rust-native-migration-report-20260603.md`
