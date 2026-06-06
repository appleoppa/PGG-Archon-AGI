# Private mirror repair pattern for external repo absorption

Use when an upstream external repo is useful but fails its own integrity checks or has a small packaging/manifest defect.

## Pattern

1. Keep upstream evidence immutable:
   - record upstream URL, branch/tag, commit SHA, license, file count, and failing test output;
   - do not rewrite the upstream clone history as if it originally passed.
2. Create or update a private backup/mirror repository before applying local repairs.
3. Apply the smallest repair in the private mirror only, with a clear commit message.
4. Re-run the same tests that failed upstream plus syntax checks.
5. Push the repaired private branch and read back remote visibility (`PRIVATE`) and pushed head.
6. Report two statuses separately:
   - upstream status: original result, including failures;
   - private mirror status: repaired/tested result.
7. Absorb only the reusable pattern unless a separate security review approves installation.

## Pitfalls

- Broad `.gitignore` rules such as `memory/` can ignore a legitimate skill directory like `skills/memory/`; use `git check-ignore -v` and `git add -f <path>` when intentionally adding that path.
- If different `python3` executables are on PATH, a retry with the known interpreter used earlier is valid, but record which interpreter produced the passing test.
- Do not let a private repair erase the truthful statement that upstream failed before repair.

## Evidence fields to capture

- upstream SHA/tag
- private repo URL and visibility
- private repair commit SHA
- before/after test counts
- license
- installed/enabled status
- remaining blockers
