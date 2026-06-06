# APEX-SKILL remote mirror comparison pattern

Use this reference when comparing two GitHub mirrors/forks of an external capability repo such as `appleoppa/APEX-SKILL-private-backup` vs `appleoppa/APEX-SKILL` before absorption or fusion.

## Why this matters

Two mirrors may share the same upstream root but diverge by non-fast-forward local commits. Do not infer freshness from repo name alone. Compare metadata, branches, tags, commit graph, file tree, content diff, and real test output.

## Minimal evidence checklist

1. Confirm access and repository metadata:
   - `gh repo view OWNER/REPO --json nameWithOwner,description,isPrivate,isArchived,defaultBranchRef,createdAt,updatedAt,pushedAt,url`
   - `gh api repos/OWNER/REPO/branches --paginate --jq '.[] | [.name, .commit.sha, (.protected|tostring)] | @tsv'`
   - `gh api repos/OWNER/REPO/tags --paginate --jq '.[] | [.name, .commit.sha] | @tsv'`
   - `gh api repos/OWNER/REPO/languages`
2. Clone into hidden workspace, not Home root, e.g. `~/.hermes/workspace/repo-diff/<topic>/`.
3. Add the other clone as a temporary remote so ancestry is valid inside one Git database:
   - `git remote add backup ../backup || true`
   - `git fetch backup --tags`
   - `git log --oneline --decorate --graph --all --max-count=30`
   - `git log --oneline backup/main..main`
   - `git log --oneline main..backup/main`
   - `git merge-base main backup/main`
4. Compare tracked files and code size:
   - `git ls-files | wc -l`
   - `git diff --shortstat backup/main main`
   - `git diff --stat --find-renames backup/main main`
   - `git diff --name-status --find-renames backup/main main`
5. Inspect semantic docs before summarizing:
   - `CHANGELOG.md`
   - `docs/AUDIT.md`
   - `SECURITY.md`
   - migration docs such as `docs/RUST_MIGRATION.md`
6. Run the actual project tests in each clone and report exact results. If one clone has a test failure, state it directly; do not call the newer repo fully verified.

## Reporting shape

Use a compact table:

- repo metadata: privacy, default branch, latest commit, tags, file count, language stats
- commit relation: common ancestor, unique commits each side, fast-forward or divergent
- file/content delta: changed files, additions/deletions, new docs/scripts/tests
- verification: exact test command and result per repo
- recommendation: which repo is newer/better for absorption and what blocker remains

## Pitfalls

- `git diff --no-index` on two working directories can be noisy or misleading because it sees `.git`; prefer adding one clone as a remote of the other and diff commit refs.
- Same commit message does not mean same commit SHA or identical ancestry. In the observed APEX-SKILL comparison, both repos had a `fix: add missing memory skill manifest` commit, but with different SHAs and divergent history.
- A newer, more featureful repo can still have a failing local test. Distinguish capability richness from verified readiness.
