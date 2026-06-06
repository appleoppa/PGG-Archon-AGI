# Local multi-source → private GitHub repo sync + usage-doc integration pattern

Use when the user asks to read several local Desktop/workspace repositories or spec folders, compare them with a user-owned private GitHub repo, keep the remote complete/latest, and turn local spec notes into repository usage docs.

## Durable workflow

1. **Clone remote into hidden workspace**
   - Use a hidden work area such as `~/.hermes/workspace/repo-sync/<repo>-<timestamp>/`.
   - Read back `gh repo view`, default branch, visibility, local `git rev-parse HEAD`, and tracked file count before touching files.

2. **Inventory each local source separately**
   - For multi-repo folders, detect nested `.git` roots but do not copy `.git` directories.
   - Build a clean file inventory excluding runtime/build/cache noise: `.git/`, `target/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.venv/`, `venv/`, `.DS_Store`.
   - Compare by intended destination layout, not by raw directory name alone. Example: Desktop `1.Apex仓库` may map to remote `apex/`, Desktop `3.EVM...` to `evm/`, spec folder to `docs/evolution-specs/`.

3. **Non-destructive sync first**
   - Copy clean source files into the remote clone without deleting remote-only files unless the user explicitly authorizes pruning.
   - Treat tracked runtime state files (timestamps, heal backups, pid/db/cache outputs) as suspect. If tests or imports mutate them, restore them before commit unless the file content is a deliberate source/config change.
   - Merge ignore files instead of replacing them: preserve old ignore patterns and add new build/cache patterns such as `target/`.

4. **Turn specs into docs**
   - Preserve original spec files under `docs/evolution-specs/` or equivalent.
   - Create/update `docs/USAGE.md` as the human-facing integrated usage guide: repo structure, core loop, module entrypoints, verification commands, forbidden overclaims, completion gates.
   - Add a root `README.md` pointing to `docs/USAGE.md` when the remote root lacks a README.

5. **Repair small packaging/test-contract gaps exposed by verification**
   - If a subproject test expects a public import package but source files are flat or differently cased, prefer adding a small compatibility package (e.g. `gene_nexus/__init__.py`) that re-exports existing implementation modules, instead of moving many source files.
   - If a formula collapses first-run output to zero due to a multiplier that should be neutral when no signal exists, make the zero-signal case an explicit neutral factor and add a short rationale in code.

6. **Verification gates before push**
   - Run project-root tests for nested projects instead of one monolithic pytest when imports are project-local.
   - Run targeted `py_compile` for script-like modules when no full test suite exists.
   - Run Rust `cargo check` with the user's known cargo path if PATH may omit cargo.
   - Run a changed-file secret-pattern scan before commit.
   - Check for tracked runtime/build garbage with `git ls-files | grep -E '(^|/)(\.DS_Store|__pycache__|\.pytest_cache|target/)'`.

7. **Scoped commit + remote readback**
   - Stage only the intended files.
   - Commit and push.
   - Verify local and remote branch SHAs match with `git ls-remote origin refs/heads/<branch>`.
   - Use GitHub API content readback for newly added docs/spec/package files and, when useful, decode first lines of README/USAGE.

## Reporting contract

Report:
- remote repo, visibility, branch, commit SHA;
- what local sources mapped to which remote directories;
- files/docs added or updated;
- verification commands and exact pass/fail counts;
- warnings that remain (for example compiler warnings) without calling them failures;
- remote readback evidence;
- boundaries: do not claim external AGI benchmark success or production readiness from repository sync/tests alone.

## Pitfalls

- A single pytest from repo root can fail because nested projects assume their own working directory/import path. Diagnose and rerun from each project root before calling code broken.
- Test runs may mutate state JSON timestamps; restore those before staging.
- Copying `.gitignore` from a local source can accidentally drop existing ignore entries. Merge it.
- Do not push Desktop cache/build artifacts merely to keep the repo “complete”; completeness means complete source/spec/docs, not runtime residue.
