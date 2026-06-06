# Claude-guided unresolved-gap formula gate pattern (2026-06-06)

## Trigger

Use when the user asks to “代入公式”, “和 Claude 一起找最大短板”, “继续进化”, or complains that the /goal rule is not visibly being executed.

## What happened

A formula status panel was already counting recent Manifest `PASS_*` family entries and reporting a clean-looking PASS. A real Claude Opus review identified the biggest gap: the panel over-counted PASS-family evidence while hiding unresolved landing gaps such as `PARTIAL`, `DEFAULT_OFF`, `DISABLED`, `502`, “no provider substitution”, or “route-enforce remains disabled”.

## Reusable fix pattern

1. Build a state pack before calling Claude:
   - formula panel JSON
   - recent `EVOLUTION_MANIFEST.json` `latest_*` entries
   - git status/log
   - excerpts of relevant status/gate/provider modules
   - explicit questions mapped to 总纲1 dimensions and 总纲2 stages.
2. Call Claude as a real provider and require strict JSON:
   - `verdict`
   - `biggest_gap`
   - `dimension`
   - `evolve_stage`
   - `recommended_fix`
   - `test_plan`
   - `forbidden_claims`
   - `risk_level`
   - `can_commit_files`.
3. Treat Claude’s result as an audit input, not automatic truth. Implement only low-risk, read-only/status-surface changes unless the user authorized deeper runtime changes.
4. For formula/status panels, distinguish:
   - `PASS` / `PASS_*` evidence
   - exact `PASS`
   - unresolved gaps.
5. Downgrade AGI/evolution/system/route/provider tasks to `WATCH` when recent Manifest contains unresolved gaps, even if `PASS_*` evidence exists.
6. Render a short unresolved preview so the user sees the real shortfall instead of a clean-looking status.
7. Add unit tests for:
   - `PASS_*` with no unresolved gaps can still PASS
   - `PARTIAL` / `DEFAULT_OFF` / `502` / provider-substitution blockers force WATCH for AGI/evolution tasks
   - render output includes unresolved count/preview
   - status panel remains read-only.
8. After commit, update Manifest with Claude review facts, tests, commit hashes, and truth boundary.

## Durable lesson

`PASS_*` is not enough. In AGI/evolution work, a correct formula gate must surface unresolved gaps and may need to show `WATCH` as progress toward truthfulness, not regression.

## Forbidden claims

- Do not say the status panel proves T5/full AGI.
- Do not call default-off canary or fallback-window telemetry production takeover.
- Do not call cross-class fallback a GPT same-class provider substitution success.
- Do not claim official benchmark pass from internal smoke/spec tests.
