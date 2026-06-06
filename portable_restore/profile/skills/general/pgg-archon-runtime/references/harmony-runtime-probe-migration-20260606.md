# Harmony / runtime probe migration lesson (2026-06-06)

## Trigger

Use when `apex_god.measure.measure_harmony()` or a PGG/APEX runtime status surface reports:

- `components=11/12` or similar after a runtime rename/migration;
- `imports=fail` for historical names such as `APEX_GODAgent` / `apex_god_wrap`;
- a stale launchd/plist path like `apex_god/ops/launchd/com.appleoppa.apex-god.ars.plist` after the real runtime moved to a Rust-native watcher.

## Durable lesson

Do **not** restore fake legacy plists, old overlay directories, or historical sessions just to make a status score look better. First decide whether the probe is stale or the capability is actually absent.

## Correct repair pattern

1. Reproduce the status surface directly and collect both component flags and import stderr.
2. Identify whether the missing component is a historical path mismatch. For current PGG/APEX runtime, the valid active watcher signal may be:
   - `launchctl list ai.hermes.evol-watcher` succeeds;
   - `~/Library/LaunchAgents/ai.hermes.evol-watcher.plist` exists;
   - Program points at `~/.hermes/apex-evolution-engine/target/release/apex13 fused-watch`.
3. Update the probe to accept either the legacy signal or the current real runtime signal. This is a probe migration, not a capability claim.
4. If an old import-smoke name is expected, export a compatibility alias only when it points to a real current implementation. Example pattern:
   - `APEX_GODAgent = LLMKernel`
   - `apex_god_wrap = wrap_provider`
   Add boundary comments that importing these names proves only import compatibility, not provider routing or AGI capability.
5. Add a targeted regression test for:
   - legacy exports importable;
   - Harmony reports `components=12/12` and `imports=ok` when current watcher is active.
6. Verify with import smoke, `py_compile`, targeted pytest, and a fresh `measure_all()` readback.

## Scoring boundary

A fixed Harmony score is still an internal runtime/governance status score. It must not be reported as an external AGI benchmark, full AGI proof, legal correctness proof, or provider-routing proof.

## Growth metric caution

If `Growth` drops after the user intentionally cleaned historical sessions/logs, do not restore deleted session history to inflate the score. Treat this as a metric-design issue: distinguish healthy retention cleanup from capability regression, and revise the scoring method only with explicit evidence and boundary language.
