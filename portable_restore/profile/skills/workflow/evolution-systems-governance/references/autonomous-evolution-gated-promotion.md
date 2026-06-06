# Autonomous Evolution Gated Promotion Pattern

Use this reference when a PGG Archon / APEX / AGI evolution task progresses from failed examples toward GeneDB promotion.

## Durable pattern learned

A truthful autonomous evolution loop should be staged as explicit gates, not described as a single finished AGI capability:

1. Failed example captured as replayable queue item.
2. Queue item converted into read-only repair proposal.
3. Proposal converted into targeted regression fixture / BenchmarkTask.
4. Regression fixture converted into read-only patch candidate plan.
5. Patch candidate checked by sandbox readiness gate.
6. Candidate patch applied only in a temporary git worktree first.
7. If temp worktree verification passes, apply a scoped patch to the main worktree.
8. Run tests / py_compile / diff check and commit only scoped files.
9. Insert GeneDB entry only as `candidate` unless promotion gates pass.
10. Promotion requires a separate read-only promotion gate and independent visible verification.

## Critical boundary

Do not equate any earlier stage with final promotion:

- Queue exists ≠ repair exists.
- Proposal exists ≠ patch exists.
- Sandbox PASS ≠ main worktree applied.
- Main patch committed ≠ GeneDB promoted.
- GeneDB candidate ≠ verified/promoted gene.

## Claude / model verification gate

When the user asks to include Claude verification, make a real provider call and save the evidence. If Claude returns HTTP 403 / exhausted / empty output, record it as a blocker. Do not pretend Claude participated. Promotion review should remain blocked when a required independent model has no visible verification output.

## Recommended gate result labels

- `PASS_WITH_BOUNDARY`: capability works inside stated boundary.
- `PASS_PATCH_SANDBOX`: candidate patch applied only in temporary worktree and verification passed.
- `PASS_CANDIDATE_ONLY`: GeneDB candidate inserted but not promoted.
- `BLOCKED_PROMOTION_REVIEW`: promotion requirements not met.

## Verification checklist

Before reporting completion, read back concrete evidence:

- artifact paths and SHA256 where useful;
- test command output;
- git commit hash if committed;
- manifest entry/readback;
- DB row and lifecycle state for GeneDB changes;
- model call evidence for GPT/Claude/etc., including failures.
