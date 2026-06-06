# Phase10 Safe Core-Takeover Fuse

## When to use

Use this pattern when a PGG Archon / ultimate-evolution sidecar chain reaches a point that sounds like "auto core takeover", "core promotion", "scheduler/main-loop integration", or similar high-impact capability.

## Durable lesson

Do not convert a healthy sidecar score into Hermes core mutation by default. Core takeover requires a separate safety fuse:

- upstream sidecar gates are healthy;
- explicit human authorization is present;
- rollback plan is present;
- no secret/provider mutation is required;
- the output remains an evidence report/GeneDB row unless all gates pass.

If authorization or rollback is absent, the correct result is a blocked safety state, not a failed task.

## Recommended gate shape

Fields:

- `schema`: `PGGArchonUltimateEvolutionPhase10SafeCoreTakeoverFuse/v1`
- `status`: `core_takeover_blocked` or `core_takeover_authorized`
- `decision`: `hold_sidecar_only_no_core_mutation` or `allow_guarded_core_takeover`
- `gates`:
  - `phase9_ci_drift_gate_passed`
  - `core_loop_mutation_forbidden_by_default`
  - `explicit_human_authorization_present`
  - `rollback_plan_present`
  - `no_secret_or_provider_mutation`
- `blockers`: every false gate
- `boundary`: must explicitly say no `run_agent.py`, scheduler, main-loop, provider, secret, or security-boundary mutation by default.

## Verification pattern

1. Unit-test both blocked and authorized paths.
2. Add idempotent persistence/readback if a GeneDB row is written.
3. Run the sidecar CLI/script with the new phase flag.
4. Read back the generated report and GeneDB row.
5. Treat `core_takeover_blocked` as PASS when blockers are authorization/rollback boundaries.

## Pitfalls

- Do not call a blocked Phase10 a deployment failure when it correctly enforced the safety boundary.
- Do not fabricate human authorization from prior generic "continue" commands; core-loop mutation needs explicit scope.
- Do not edit protected Hermes core files while only implementing a safety fuse.
