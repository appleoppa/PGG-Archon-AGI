# Controlled AGI Roadmap V3 — Main Patch Dry-Run Gate

## Trigger

Use after V2 has produced a `PGGArchonReviewBundleResult/v1` with:

- `status = READY_FOR_HUMAN_MAIN_PATCH_REVIEW`
- no blockers
- target files listed
- LLM quorum already PASS

## Goal

Add a read-only bridge between review bundle and any future approved main patch transaction.

The bridge must prove the candidate diff can apply to the current main worktree without actually applying it.

## V3-P0 pattern

1. Read current baseline first:
   - `python -m agent.pgg_archon_autonomous_status --output <status.json>`
   - read review bundle JSON
   - `git status --short`
2. Build a dedicated module, not an ad-hoc script:
   - `agent/pgg_archon_main_patch_dry_run.py`
   - schema: `PGGArchonMainPatchDryRunResult/v1`
3. The module reads:
   - review bundle
   - readiness package
   - `patch_diff` / `candidate.diff`
4. It runs only:
   - `git apply --check <candidate.diff>`
   - `git status --short` before and after
5. PASS only if:
   - review bundle is READY
   - bundle has no blockers
   - diff exists and is non-empty
   - diff targets match bundle targets
   - `git apply --check` exits 0
   - worktree status before/after is identical
6. It must not:
   - run `git apply`
   - commit
   - write GeneDB
   - call providers
   - claim full AGI

## Test fixture pitfall

When constructing artificial diffs in tests, do not build paths through naive string replacements on absolute temp paths. That can create invalid paths such as:

- `aa/tests/...`
- `bb/tests/...`
- `atests/...`
- `btests/...`

Prefer deterministic patch generation with `difflib.unified_diff`, then explicitly prepend:

```text
diff --git a/<target> b/<target>
index 0000000..1111111 100644
--- a/<target>
+++ b/<target>
```

This catches the real target parser while still allowing `git apply --check` to run in a temporary repo.

## Debugging rule for empty-output command failures

If a combined validation command exits 1 with empty/truncated output, do not repeat it unchanged.

Decompose into:

1. unit test only with `-vv`
2. real CLI smoke
3. readback JSON summary
4. `py_compile`
5. `git diff --check`
6. `git status --short`

Only after the failing component is visible should you patch.

## Context compression pitfall

Compressed todo state may be stale. Before continuing after context compaction, reconcile actual state from:

- dashboard
- manifest
- latest git commits
- real gate JSON outputs

Do not trust the preserved todo list over the manifest/dashboard/git evidence.

## Evidence pattern

A closed V3-P0 should produce:

- real dry-run JSON under workspace
- report under workspace
- manifest capability update
- related tests passing
- scoped commit

Example compact status:

```text
V3-P0  main patch dry-run simulator  PASS
real   PASS_MAIN_PATCH_DRY_RUN
apply  git apply --check exit 0
tree   unchanged
```
