# Autonomous Evolution Loop and Promotion Gate Pattern — 2026-06-04

## Trigger

Use this reference when PGG Archon/Hermes evolution work moves beyond audit into background automation, failed-example queues, patch candidates, or GeneDB promotion.

## Durable lesson

Do not treat “module exists” or “candidate exists” as evolution completed. The safe AGI-evolution ladder should be explicit and evidence-gated:

1. Deep state audit first: manifest, repo HEAD, Rust watcher, launchd, cron jobs, existing artifacts, key imports/tests.
2. Failed sample enters replayable queue.
3. Queue item becomes read-only evolution proposal.
4. Proposal becomes targeted regression fixture.
5. Regression fixture becomes read-only patch candidate.
6. Candidate passes sandbox readiness.
7. Candidate patch applies only in a temporary git worktree.
8. Only PASS sandbox diff may be applied to the main worktree.
9. Main patch must add a live test/fixture, not a dead artifact.
10. Verified main patch can enter GeneDB only as `candidate` first.
11. Promotion requires an explicit promotion gate and independent model feasibility threshold.

## Multi-LLM promotion threshold pattern

When user requires all-LLM validation before GeneDB promotion:

- Call all configured channels separately; active chat model does not count as independent provider evidence.
- Record HTTP status, visible output length, raw hash, and classified verdict per model.
- A failed channel (e.g. Claude HTTP 403/account exhausted) is `ERROR`, not a hidden pass.
- If the user sets “two or more LLMs must pass”, do not promote unless at least two visible outputs classify as PASS.
- If fewer than required PASS, write a BLOCKED report and manifest audit record; do not mutate `gene_lifecycle.state`, `promoted_at`, or `promotion_chain`.

## GeneDB candidate vs promoted boundary

For `~/.hermes/data/pgg_archon.db` style lifecycle stores:

- `genes` row + `gene_lifecycle.state='candidate'` is candidate-only.
- `promoted_at=null` means not promoted.
- Promotion must be a separate transaction with backup, readback, promotion_chain insert, and manifest update.
- A read-only promotion gate may return `READY_FOR_PROMOTION_REVIEW`, but that is still not promotion.

## Patch sandbox detail

A useful low-risk patch type is regression fixture installation:

- Generate `tests/fixtures/pgg_archon_regressions.jsonl` in a temp git worktree first.
- Run verification commands there.
- Use `git add -N <newfile>` inside the worktree so `git diff` captures new untracked files without staging content for commit.
- Apply to main worktree only after PASS and then add a test that loads/scores the fixture.

## Common pitfalls

- Do not continue adding modules before showing what is already complete; user explicitly corrected this.
- Do not downgrade “Claude unavailable” into “Claude passed”; keep the gap visible.
- Do not let alternate model review auto-promote. Alternate model can unlock review only if explicitly allowed and logged.
- Test counts from different stages are not comparable; rerun the current same test set before using counts as evidence.
- Do not commit workspace reports/manifest unless they are repo files; update external ledgers separately and commit only current-theme repo files.
