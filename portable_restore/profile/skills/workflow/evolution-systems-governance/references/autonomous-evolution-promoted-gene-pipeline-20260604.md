# Autonomous evolution promoted-gene pipeline pattern — 2026-06-04

## When to use

Use when a PGG/Hermes evolution task must move from benchmark failures into a safe autonomous improvement loop without overclaiming AGI.

## Class-level pipeline

Target pipeline:

`queue v2 → proposal → targeted regression → patch candidate → sandbox readiness → temp worktree patch → promotion readiness package → gated main patch/GeneDB candidate/promotion`

Hard boundary:

- Background/no-agent loop may automatically reach `promotion_readiness_package`.
- Main worktree patch, GeneDB candidate insertion, and GeneDB promotion require explicit gates and evidence.
- Never collapse these states into “AGI complete”.

## Proven modules/patterns

1. Replayable queue items
   - Include prompt, expected, prediction, scorer, score_delta, priority, input_hash, failure_reason, next_action, promotion_gate, boundary.

2. Proposal worker
   - Read-only conversion from failed example to repair proposal.
   - Produces JSON/JSONL and CLI output.

3. Targeted regression generator
   - Join proposal + source queue by input hash.
   - Rebuild deterministic BenchmarkTask fixtures.
   - Verify old prediction fails and truthful repaired response passes.

4. Patch candidate sandbox
   - Convert regression fixture into read-only patch plan.
   - No edits, no provider calls, no GeneDB writes.

5. Patch sandbox readiness
   - Check target surfaces, repo boundaries, verification commands.
   - Return PASS_READY_FOR_ISOLATED_PATCH before temp worktree apply.

6. Temp worktree patch apply
   - Use `git worktree add --detach`.
   - Apply candidate patch only inside temp worktree.
   - Generate diff and run verification commands.
   - Main worktree remains untouched.

7. Promotion readiness package
   - After temp worktree patch PASS, assemble a read-only package containing queue/proposal/regression/candidate/sandbox/patch diff evidence.
   - Status is `READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW` only if every evidence file and pass condition exists.

8. GeneDB promotion transaction
   - Implement as reusable module, not one-off script.
   - Require LLM summary decision `PROCEED_PROMOTION_TRANSACTION` and visible pass quorum.
   - Backup DB, `BEGIN IMMEDIATE`, conditional update `state='candidate' AND promoted_at IS NULL`, insert `promotion_chain`, read back.
   - Already promoted genes should return `ALREADY_PROMOTED_VERIFIED` without duplicate chain rows.

9. Status dashboard
   - Provide read-only CLI aggregating manifest, latest loop ledger, GeneDB lifecycle, cron job, Rust watcher, latest readiness package and known gaps.

## Multi-LLM quorum discipline

- If the user requests all available LLMs, call real providers and save evidence per model.
- Claude Responses provider may be unavailable due to upstream `HTTP 403 All available accounts exhausted`; do not call this “fixed” locally unless a live call succeeds.
- If the user explicitly authorizes fallback, record that authorization in the LLM summary and gate decision.
- Promotion requires at least the configured quorum of visible PASS outputs. Failed/empty/error calls do not count.

## Critical pitfall: fixture replacement

When applying generated regression fixtures, do NOT overwrite `tests/fixtures/pgg_archon_regressions.jsonl` wholesale. That deletes prior regression samples and can make existing tests fail.

Correct pattern:

- Load existing JSONL by `task_id` preserving order.
- Merge/upsert new tasks by `task_id`.
- Write merged JSONL with trailing newline.
- Tests must prove both old and new task IDs remain present in the temp worktree while the main repo remains untouched.

## Manifest discipline

If a gate has historical blocked evidence and a later authorized fallback passes, do not erase history. Store layered state, e.g.:

- `four_llm_status = BLOCKED_CLAUDE_403_AND_THRESHOLD_UNMET`
- `b_fallback_status = PASS_3_OF_3`
- `latest_decision = PROCEED_PROMOTION_TRANSACTION_UNDER_USER_AUTHORIZED_B_FALLBACK`

This prevents dashboards from reporting contradictory stale status.

## Verification checklist

Before reporting completion:

- Targeted pytest suite passes.
- `py_compile` passes for new modules.
- `git diff --check` passes.
- Smoke run proves the pipeline reaches the claimed stage.
- Manifest updated and read back.
- Scoped commit contains only relevant repo files.
- Report says which states are complete and which remain gated.
