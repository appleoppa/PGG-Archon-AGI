# Mixed Workspace Governance Batching Pattern (2026-06)

Use when a Hermes Agent / PGG Archon workspace has hundreds of mixed uncommitted files and the user wants "continue / full processing" without unsafe deletion or blind commit.

## Durable pattern

1. Keep source code, tests, evidence packs, core runtime, and historical phase files in separate batches.
2. Generate an evidence directory under the relevant workspace, not Desktop and not repository root.
3. For each candidate batch, require:
   - explicit file list;
   - import check where applicable;
   - direct test/reference mapping;
   - targeted test run through the project venv/test runner;
   - `git add --dry-run -- <explicit files>`;
   - readback that staged files are still empty when the user has not authorized real staging.
4. Do not use `git add .` in mixed workspaces.
5. Treat core runtime/tool-surface files as HOLD until separately reviewed.
6. Treat historical phase backlogs by paired source+test subsets first; leave source-only and test-only files unmodified until their references are audited.
7. Record blocker/non-blocker categories separately: `commit_ready`, `needs_tests_or_reference_mapping`, `needs_safety_review`, `HIGH_HOLD`.

## Batch taxonomy that worked

- Batch C: independent modules with source+tests.
- Batch C2: remaining independent modules after adding direct tests or mapping notes.
- Batch D: core runtime/tool surface (`run_agent.py`, `mcp_serve.py`, tool registry surfaces, runtime sequence files); HOLD and review one by one.
- Phase backlog: process only source+test paired phase ranges first.

## Rollback patch pitfall

When creating rollback evidence for modified tracked files, do not round-trip patch text through JSON/write helpers if byte fidelity matters. Generate exact patch files with shell redirection:

```bash
git diff -- path/to/file.py > evidence/path__to__file.py.patch
git apply --reverse --check evidence/path__to__file.py.patch
```

If `git apply --reverse --check` fails with "patch corrupted" after a tool-written patch, regenerate via direct shell redirection and re-check before reporting rollback readiness.

## Safety reporting

When an earlier verification attempt was wrong, preserve the correction chain instead of hiding it:

- mark older evidence as superseded;
- create v2/v3/v4 evidence with a `fix_note`;
- make the latest authoritative file explicit in the final report.

## Completion boundary

Unless the user explicitly authorizes irreversible actions, "full processing" means full audit/test/dry-run/evidence closure only:

- no real `git add`;
- no commit;
- no push;
- no deletion;
- no Desktop sync;
- no rollback application.
