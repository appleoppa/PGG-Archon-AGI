# GitHub repo private mirror + local Python package deployment pattern

## Context captured

A user may ask to copy a public GitHub repository into their own private GitHub and then ask whether it is deployed locally. The durable pattern is not the specific repository, but the completion gates and verification sequence.

## Recommended sequence

1. Verify GitHub CLI auth and target owner.
2. Clone the source into a clean workspace path, not the home/root directory.
3. Create or reuse the target private GitHub repository.
4. Push refs to the private repository.
5. Read back remote metadata: `isPrivate`, URL, default branch, local HEAD, remote HEAD, and match status.
6. For local deployment, inspect README/project files, create an isolated environment, install the package, run tests, then run a minimal live smoke test.
7. If deployment tests reveal small, low-risk correctness bugs, fix them, rerun tests, and push only the relevant files.
8. Clean generated artifacts and ignore local-only files (`.venv/`, `__pycache__/`, `.pytest_cache/`, `*.db`, `.DS_Store`) before committing.

## Verification evidence to report

- Local path.
- Environment path.
- Target GitHub URL.
- Private status read back from GitHub.
- Test result count.
- Smoke-test result, e.g. write/search/read or import/instantiate/run.
- Local HEAD and remote HEAD, with match status.

## Pitfalls

- Do not treat cloning or repo creation as deployment. Deployment requires install/import/runtime exercise.
- Do not treat file existence as functionality. Run tests and a minimal live call.
- `git push --mirror` is appropriate for a new empty private mirror, but can overwrite refs in an existing repo; for existing repos, verify scope before destructive mirror pushes.
- Some upstream repos accidentally track generated files such as `__pycache__`; remove them from the private copy during cleanup if you are already committing deployment fixes.
- If tests fail due to small source bugs and the user asked whether it is deployed, fix low-risk issues instead of stopping at a failure summary.
