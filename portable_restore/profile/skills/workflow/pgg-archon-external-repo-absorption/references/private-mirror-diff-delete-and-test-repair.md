# Private mirror diff/delete + local test repair pattern

Use when the user asks to compare two user-owned GitHub mirrors/forks, delete the obsolete one, and repair the surviving mirror locally.

## Pattern

1. **Remote identity and metadata first**
   - Read both repos with `gh repo view <owner>/<repo> --json ...`.
   - Read branches/tags/languages with `gh api repos/<owner>/<repo>/branches`, `/tags`, `/languages`.
   - Record privacy, default branch, branch head SHA, tag set, pushedAt.

2. **Clone into hidden workspace, not Home root**
   - Use a hidden or governed workspace path, e.g. `~/.hermes/workspace/repo-diff/<topic>/`.
   - Do not create visible Home-root comparison folders.

3. **Compare commit graph before file diff**
   - Add the older mirror as a second remote in the surviving clone or clone both repos.
   - Run:
     - `git log --oneline --decorate --graph --all --max-count=...`
     - `git merge-base <a> <b>`
     - `git log <a>..<b>` and `git log <b>..<a>`
   - If SHAs diverge but commit messages match, treat them as separate commits until file/tree equality is proven.

4. **Compare files and content**
   - Prefer `git diff --stat --find-renames <oldref> <newref>` and `git diff --name-status --find-renames <oldref> <newref>` after both histories are visible in one repo.
   - For two independent working trees, `git diff --no-index` can miss `.git`-controlled comparison semantics; use remote refs when possible.

5. **Delete only after user-owned target is confirmed**
   - For deletion requests, verify the repo is user-owned and exact name matches.
   - Run `gh repo delete <owner>/<repo> --yes` only for the named obsolete mirror.
   - Read back deletion with `gh repo view <owner>/<repo>`; expected confirmation is “Could not resolve to a Repository”.

6. **Repair surviving repo with scoped changes only**
   - Reproduce failing tests first.
   - Fix the underlying durable issue, not just the assertion, unless the assertion is the defect.
   - Run the focused failing test, then the full suite.
   - Use `git diff --check` and `git status --short` before commit.
   - Commit only the files touched by the repair and push.
   - Verify remote head with `git ls-remote origin refs/heads/<branch>` and repo metadata with `gh repo view`.

## Durable debugging lesson: import-time path constants

Python CLIs that read environment-derived paths at import time can break embedded tests or in-process runners that set `os.environ` after import. A robust pattern is:

- Keep a single source of truth for base path, e.g. `APEX_HOME`.
- Provide `sync_paths()` to recompute derived constants from current `APEX_HOME`.
- Provide `refresh_paths_from_env()` for CLI entrypoints to call after environment setup.
- Let test harnesses that mutate the module variable directly call `ensure_dirs()`/`sync_paths()` so derived paths stay aligned.

Do not globally refresh from environment inside every helper if tests also assign module variables directly; that can override the sandbox and make earlier seeded files invisible.

## Report fields

Return a concise table with:

- deleted repo readback result
- surviving repo URL/privacy/default branch
- local test before/after
- commit SHA pushed
- remote head readback
- remaining blockers
