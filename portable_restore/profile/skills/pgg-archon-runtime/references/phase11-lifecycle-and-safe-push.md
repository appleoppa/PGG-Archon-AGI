# Phase11 lifecycle chain and safe push pattern

## Trigger

Use this when continuing PGG Archon / ultimate evolution work after Phase9/Phase10, especially when the user says “继续” and the next low-risk step is to persist lifecycle/promotion evidence, test, commit, and push.

## Durable lesson

Phase11 must not only write workspace reports or mutate helper tables. It should create an auditable gene lifecycle surface:

1. Build/read current lifecycle state.
2. Ensure `gene_lifecycle` and `promotion_chain` schemas exist idempotently.
3. Enroll orphan `ultimate_evolution_formula%` genes as `candidate`.
4. Promote the Phase5 promotion gate gene to `active` when present.
5. Insert an idempotent Phase11 gene row, e.g. `ultimate_evolution_formula_phase11_gene_lifecycle_chain`.
6. Re-read DB counts and the inserted gene row before claiming completion.
7. Evaluate the gate after persistence, not against the stale pre-enrollment snapshot.

## Verification pattern

Minimum evidence before reporting complete:

- Targeted pytest covering lifecycle gate and persistence.
- `py_compile` for touched Python modules/scripts.
- Run the ARS cycle through Phase11 with `--persist`.
- SQLite readback:
  - Phase11 gene id/name/quality_score.
  - `gene_lifecycle` state counts.
  - `promotion_chain` event count.
- `git diff --check`.

## Commit/push boundary

If the local branch is behind the public upstream (`origin/main`) by many commits, do **not** force-push or directly push to upstream main as part of autonomous evolution. Commit locally, then push the verified commit to a private feature branch and verify with `git ls-remote`.

Safe pattern:

```bash
git add -- <only this round's files>
git diff --cached --name-status
git commit -m "Phase11 gene lifecycle chain and fallback guardrails"
git push private HEAD:refs/heads/pgg-archon-phase11-lifecycle-<timestamp>
git ls-remote --heads private pgg-archon-phase11-lifecycle-<timestamp>
```

## Artifact hygiene

Root-level runtime artifacts such as transient debate JSON, empty local DB files, or unintegrated legacy source candidates should be archived under `workspace/存档/<run>/` with a `MANIFEST.json` rather than deleted or committed.

Untracked `workspace/` history may remain uncommitted if it is process evidence or legacy workspace material; do not let it block code commit, but explicitly state it was excluded from commit scope.
