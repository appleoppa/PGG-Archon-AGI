# Private Mirror + Local Delta Cherry-Pick Pattern

Use when the user asks to save an external GitHub repo into their own private remote and also compare a local copy for useful commits.

## Durable lesson

Do not blindly push the local working copy over the new private mirror. A local copy may be behind upstream while still containing one useful local commit. Preserve upstream first, then apply only the verified local delta.

## Workflow

1. Verify GitHub identity and source repo metadata.
2. Create or reuse the user's private target repo.
3. Prefer `git clone --mirror <source>` + `git push --mirror <private>` for small/stable repos so branches and tags are preserved.
4. Inspect the local copy:
   - `git rev-parse HEAD`
   - `git status --short`
   - `git log --oneline --decorate --graph --all -20`
   - compare local HEAD, upstream/private HEAD, and merge-base.
5. If local is behind upstream but has useful local commits:
   - clone the private mirror to a fresh worktree;
   - fetch the local commit by SHA from the local repo path;
   - `git cherry-pick <local_sha>` onto the private repo's current default branch;
   - do not force-push the older local branch over the newer private mirror.
6. Run at least targeted tests for the touched area and `git diff --check`.
7. If full upstream tests fail, test the upstream/private baseline at the pre-delta commit. If the same failures exist before the local delta, report them as pre-existing upstream baseline failures, not regressions from this session.
8. Push and read back:
   - `isPrivate/visibility`
   - default branch
   - remote HEAD SHA and commit message
   - tags/branches preserved
   - compare result showing the private repo is ahead by only the intended delta.

## Reporting discipline

Report the private repo URL, privacy status, remote HEAD, what was mirrored, what local delta was applied, and which tests are clean vs. pre-existing baseline failures. Do not claim full regression pass when the upstream baseline itself fails.
