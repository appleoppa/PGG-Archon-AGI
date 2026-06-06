# APEX ΔE convergence, score semantics, and workspace-root pitfalls

Use this when evaluating or repairing `hermes_apex_evolution` / background evolution convergence.

## Durable lessons

1. **APEX ΔE is higher-is-better.**
   - The generic `ConvergenceChecker` used in `apex_god.middleware.convergence_bridge` treats inputs as lower-is-better gaps/errors.
   - Do not feed raw `apex_delta_e` directly into a lower-is-better convergence slope check; an improving ΔE can be falsely labelled `diverging`.
   - Convert first: `apex_delta_e_gap = max_delta_e - apex_delta_e` (current target used in the session: `max_delta_e = 5.0`).
   - Keep the raw `delta_e` in `current_eval` for transparency, and add a `convergence_metric` object describing the gap.

2. **Infrastructure scores are not capability/external-audit scores.**
   - `status.score.score` from pgg-background-evolution is an infrastructure/background readiness score.
   - Label it explicitly, e.g. `score_type = infrastructure_readiness` and `benchmark_type = runtime_health_not_external_audit`.
   - In deviation checks, treat this score as `infrastructure_reference` only. Compare self-eval against an actual external/model audit score such as `manifest_summary.latest_gpt_audit` when available.

3. **Workspace-root path matters for Rust evaluate.**
   - `eval.rs` joins `workspace.join("evolution")` internally.
   - Calling `py_evaluate("~/.hermes/workspace/evolution", out)` makes the evaluator look at `~/.hermes/workspace/evolution/evolution`, producing false low scores such as `alpha_psi=0`, `lambda_phi=0`.
   - Correct default call shape: `py_evaluate("/Users/appleoppa/.hermes/workspace", out)` or CLI `apex13 eval --workspace /Users/appleoppa/.hermes/workspace --output ...`.
   - Audit Python wrappers and background callers (`tools/apex_evolution_tool.py`, pgg-background-evolution scripts, Rust `background.rs`) for this root-vs-child mismatch.

4. **After rebuilding the Rust binary, restart the launchd watcher if the running process must use the change.**
   - Build/readiness alone does not prove the long-lived watcher process has loaded the new binary.
   - Verify with `launchctl list ai.hermes.evol-watcher` and process PID/elapsed time after `kickstart -k`.

## Verification pattern

Minimum readback for a real fix:

- `cargo check` and release build pass.
- `apex13 eval --workspace ~/.hermes/workspace --output <json>` shows non-zero evidence-derived scores where expected.
- `python -m apex_god.middleware.convergence_bridge --cycle` returns a verdict based on `apex_delta_e_gap`, not raw ΔE slope.
- `python -m apex_god.health` remains 24/24.
- `EVOLUTION_MANIFEST.json` records score semantics truthfully.

## Non-goals / boundaries

- Do not claim higher AGI capability from a readiness score alone.
- Do not use `status.score.score` as an external audit score.
- Do not hide residual values such as `evol_code=0.0` or stale `lambda_phi`; preserve them as real gaps.
