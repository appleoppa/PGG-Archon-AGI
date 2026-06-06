# Hermes post-install / migration hardening — 2026-06-03

Use this reference when a new Hermes install reuses an existing `~/.hermes` tree and old overlays/cron jobs produce mixed runtime state.

## Pattern

1. **Back up before repair**
   - `config.yaml`, `.env`, `cron/jobs.json`, LaunchAgents, `hermes status`, `hermes doctor`, and `git status`.
   - Store under `~/.hermes/workspace/治理/hermes-repair-backups/<timestamp>/`.

2. **Separate active runtime from historical overlays**
   - Do not restore old Python APEX/PGG modules just because legacy cron imports fail.
   - If Rust-native `hermes_apex_evolution`/`apex13 fused-watch` has replaced the old chain, treat old Python APEX/SE20 jobs as legacy unless a separate manifest proves they are current.

3. **Install/reinstall Rust PyO3 module after venv/update churn**
   - Copy `~/.hermes/apex-evolution-engine/target/release/libhermes_apex_evolution.dylib` into current venv site-packages as `hermes_apex_evolution.abi3.so`.
   - Run `codesign --remove-signature` if needed, then `codesign --force --sign -`.
   - Verify with `import hermes_apex_evolution`, `version()`, and `py_evaluate(..., output_file)`.

4. **Guard legacy cron scripts**
   - Pausing a job is not enough; add a script-level guard so accidental resume exits safely.
   - Pattern: default exits 0 with a clear “legacy chain replaced” message unless `PGG_LEGACY_CRON_FORCE_RUN=1`.
   - Preserve the original body after the guard for auditability.

5. **Overlay manifest before movement/deletion**
   - Create a manifest of untracked PGG/APEX files with category, size, mtime, sha256/tree_sha256, reference scan hits, and delete policy.
   - Rule: `manifest_only; no code import; no delete; no restore old Python modules` until user approval and no-reference verification.

6. **Use LLM and formula evidence truthfully**
   - Track visible output separately from HTTP status. Timeout or `output=[]` is not substantive participation.
   - Use a bounded formula such as `AK_absorb` to decide low-risk actions; direct overlay deletion and production update without diff/testing should usually be blocked/deferred.

7. **Open-source learning boundary**
   - GitHub/open-source scout is read-only unless the user explicitly authorizes clone/run/import.
   - Store search JSON and README snapshots when available; rate limits are blockers, not grounds to claim full learning.

## Verification

- `hermes gateway status` shows default and profiles running.
- `hermes cron list` shows active key jobs `ok` and legacy jobs paused/guarded.
- `hermes-web-ui status` works in non-interactive shell or a wrapper supplies PATH to bundled node.
- Rust reinstall script prints module version and writes a valid evaluation JSON.
- `overlay_manifest_*.json` readback shows all items hashed and governed.

## Pitfalls

- Do not encode transient “command not found” as a durable limitation; capture the wrapper/PATH fix.
- Do not hide optional `doctor` warnings; maintain a warning register so new warnings stand out.
- Do not directly run `hermes update` while untracked overlays remain unmanaged; first do diff/backup/test-branch planning.
