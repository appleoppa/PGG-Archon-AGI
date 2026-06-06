# Controlled AGI Roadmap V3 — Approval Token, Transaction Package, Rollback Verification

## Trigger

Use after V3-P0 main patch dry-run has produced `PGGArchonMainPatchDryRunResult/v1` with:

- `status = PASS_MAIN_PATCH_DRY_RUN`
- `blockers = []`
- target files listed
- `git apply --check` already passed
- main worktree status unchanged

This reference covers the next controlled rungs:

```text
V3-P1 human approval token schema
V3-P2 approved main patch transaction package gate
V3-P3 regression + rollback verification
```

## Core lesson

Do not jump from dry-run to real `git apply`.

The safe sequence is:

```text
dry-run result
→ human approval token bound to exact evidence
→ prepare-only transaction package + rollback package
→ temporary worktree apply + verification + reverse apply rollback
→ only then consider a separately authorized main patch runner
```

Each rung is a separate capability with its own schema, tests, smoke, manifest update, report and scoped commit.

## V3-P1 pattern — Human approval token

Create a dedicated module, not an ad-hoc JSON file:

```text
agent/pgg_archon_human_approval_token.py
schema: PGGArchonHumanApprovalToken/v1
schema: PGGArchonHumanApprovalTokenValidation/v1
```

The token should bind:

- dry-run result path
- dry-run result sha256
- dry-run status
- current repo head
- target files
- human approver id
- explicit approval statement
- optional expiry
- boundary acknowledgements

Required boundary acknowledgements should include:

```text
reviewed_dry_run_result
accepts_target_files
understands_mutation_scope
requires_rollback_package
no_genedb_promotion_by_token
no_full_agi_claim
```

Important boundary:

```text
A valid token authorizes only the next transaction gate review.
It does not authorize direct git apply, commit, GeneDB promotion, provider claims, or full AGI claims.
```

## V3-P1 pitfall — repo head drift

If a module is committed after token creation, the repo head changes. A token bound to the old head may be valid for its original context but should not be reused for the next real transaction smoke.

Before V3-P2 real smoke, regenerate or validate the token against the current `git rev-parse --short HEAD`.

## V3-P2 pattern — Approved main patch transaction package

Create a prepare-only gate:

```text
agent/pgg_archon_approved_main_patch_transaction.py
schema: PGGArchonApprovedMainPatchTransaction/v1
schema: PGGArchonMainPatchRollbackPackage/v1
```

Inputs:

- valid human approval token
- V3-P0 dry-run result
- repo root

Checks:

- token validates against current repo head
- dry-run status is PASS
- patch diff exists and sha256 is captured
- diff targets match dry-run targets
- diff targets match token targets
- `git apply --check <candidate.diff>` exits 0
- main worktree status before/after is identical

Outputs:

- `approved_main_patch_transaction_package.json`
- `main_patch_rollback_package.json`
- result JSON under workspace

Boundary:

```text
Prepare-only. No git apply. No commit. No GeneDB mutation. No provider calls. No full AGI claim.
```

## V3-P3 pattern — Regression + rollback verifier

Create a temp-worktree verifier:

```text
agent/pgg_archon_regression_rollback_verifier.py
schema: PGGArchonRegressionRollbackVerificationResult/v1
```

Workflow:

1. Read transaction package and rollback package.
2. Verify transaction status and patch sha256.
3. Record main worktree status.
4. Create temporary detached git worktree.
5. Apply candidate diff inside temp worktree only.
6. Run bounded verification commands.
7. Run reverse patch: `git apply -R <candidate.diff>` inside temp worktree.
8. Confirm target hashes restored after rollback.
9. Remove temp worktree unless explicitly keeping it for debug.
10. Confirm main worktree status unchanged.

PASS only if:

```text
transaction_ready = true
rollback_package_exists = true
patch_diff_sha256_matches = true
temp_worktree_created = true
patch_applied_in_temp_worktree = true
target_hashes_changed_after_apply = true
verification_commands_passed = true
rollback_applied_in_temp_worktree = true
target_hashes_restored_after_rollback = true
main_worktree_status_unchanged = true
```

Boundary:

```text
Temp-worktree verification only. No main worktree mutation, no commit, no GeneDB mutation, no provider calls, no full AGI claim.
```

## V3-P3 pitfall — default verification commands in minimal test repos

A temp test repo may not contain the production `agent/` module tree. Do not unconditionally run:

```text
python -m py_compile agent/<module>.py
```

Pattern:

```text
if (tmp_worktree / 'agent' / '<module>.py').is_file():
    run py_compile
always run git diff --check
```

For real Hermes repo smoke, py_compile can run because the module exists. For artificial minimal repos, keep verification generic or pass explicit `verification_commands`.

## Validation discipline

For each rung:

```text
unit tests
related regression tests
real smoke using workspace evidence
py_compile
git diff --check
manifest capability update
report under ~/.hermes/workspace/evolution/...
scoped git commit
final git status --short
```

Do not rely on a combined shell command without `set -e`; otherwise later commands can hide a failed pytest. If a combined command fails or gives misleading output, decompose into unit test, CLI smoke, readback JSON, py_compile, diff check, status.

## Reporting format

Compact status block preferred:

```text
V3-P1  human approval token schema             PASS
V3-P2  approved transaction package gate       PASS_PREPARE_ONLY
V3-P3  regression + rollback verifier          PASS

Boundary:
  main patch not applied
  GeneDB not promoted
  scheduler/security boundary untouched
```

Always state explicitly whether the patch was actually applied. A transaction package or rollback verification is not the same as main patch application.
