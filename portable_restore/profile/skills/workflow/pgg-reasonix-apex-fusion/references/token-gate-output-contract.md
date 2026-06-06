# Self-Evolution Token Gate output contract

## Trigger

Use this reference when working on PGG Reasonix/APEX fusion gates, Reasonix PreToolUse hooks, self-evolution token gates, or any consumer that reads gate JSON by top-level `schema`.

## Durable lesson

A gate script can accidentally write a full manifest into a file whose name and downstream consumers expect a compact gate summary. This does not break the script, but it creates silent automation risk: strict readers see `readiness_band`, `next_stage_allowed`, or `blockers` as `null` because those fields live nested under another object.

## Required output split

Keep these as separate artifacts:

- `self_evolution_token_gate_latest.json`
  - top-level schema: `PGGArchonSelfEvolutionTokenGateReport/v1`
  - top-level fields: `status`, `readiness_band`, `next_stage_allowed`, `blockers`, `token_saving_ratio`, `field_recall`, `semantic_overlap`, `verdict_normalization_pass`, `ais_immune_score`, `fusion_manifest_path`, `fusion_manifest_sha256`
- `fusion_manifest_latest.json`
  - top-level schema: `PGGArchonReasonixApexFusionManifest/v1`
  - full Rust-owned additive fusion manifest

Do not make consumers infer the gate summary by traversing a full manifest unless the consumer explicitly declares it supports that schema.

## Verification pattern

After running `scripts/self_evolution_token_gate.sh`, verify all of the following before reporting PASS:

1. `self_evolution_token_gate_latest.json` exists and top-level schema is `PGGArchonSelfEvolutionTokenGateReport/v1`.
2. `fusion_manifest_latest.json` exists and top-level schema is `PGGArchonReasonixApexFusionManifest/v1`.
3. `next_stage_allowed == true` and `blockers == []` on the summary file.
4. `rust_owned == true` and `hermes_core_mutation == false` on the full manifest.
5. The summary's `fusion_manifest_sha256` equals the actual SHA-256 of `fusion_manifest_latest.json`.
6. Reasonix PreToolUse high-risk smoke reads the summary schema and records `status=PASS`, `gate_decision=ALLOW` for an allowed dummy event.
7. `cargo test` and `git diff --check` pass before committing script changes.

## Reusable script hook

If the crate contains `scripts/verify_gate_outputs.py`, run it after the gate script. It should emit `PGGArchonGateOutputVerification/v1` with `status=PASS` and `errors=[]`. If it is missing, recreate the same checks above as a small deterministic script rather than relying on visual inspection.

## Reporting boundary

This output contract only proves the local additive Rust gate and hook consumer are reading coherent evidence. It does not prove full AGI, Hermes core replacement, zero-risk production autonomy, or universal sidecar enforcement.
