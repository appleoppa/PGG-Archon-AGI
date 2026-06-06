# GitHub factory and multi-model verification pattern

## When to use
Use this when the user asks whether the GitHub evolution factory and multi-model route are “打通/可用”, or asks to repair/verify the GitHub-backed evolution loop.

## Core principle
Do not infer readiness from config files, local workflow files, or old run records. Verify the live path end to end:
1. Load `.env` values into the verification subprocess without printing secrets.
2. Check GitHub token authentication through the GitHub API.
3. Check the target repository exists through authenticated API access.
4. Check remote workflow metadata is visible.
5. Dispatch at least one workflow remotely and poll until completion.
6. Verify the remote run produced a new remote artifact/result, not just a local file.
7. Ping each model provider with a tiny request and report only success/failure, never key values or raw secrets.
8. If local repository pull is blocked by uncommitted work, preserve work safely before syncing.

## Safe repository sync pattern
When local uncommitted changes block pulling remote factory results:
1. Inspect changed/untracked paths.
2. Scan changed files for token/key patterns before committing or pushing.
3. Commit local work with a neutral preservation message.
4. Pull with rebase.
5. If a conflict occurs, merge the semantic rules, not just choose ours/theirs.
6. Re-scan the final commit for secrets.
7. Push only after the scan passes.
8. Pull again if a remote workflow created a new commit during the push window.
9. Verify local and remote heads match and `git status` is clean.

## Reporting boundaries
Report status precisely:
- “GitHub 工厂可用” only after a remote workflow dispatch completed successfully.
- “多模型可用” only after live tiny calls succeed for each configured model.
- “基础设施可用” does not mean a real awakening/evolution cycle completed.
- If a model or workflow is missing, say which gate is missing and mark the cycle degraded rather than complete.

## Anti-patterns
- Treating local workflow files as proof that GitHub Actions ran.
- Treating old action runs as proof of current readiness.
- Printing tokens or provider keys in diagnostics.
- Force-pulling or discarding local work to resolve a dirty tree.
- Calling a successful workflow run “进化完成”; it proves remote execution only.
