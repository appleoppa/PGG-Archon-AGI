# Local Git Snapshot Discipline for Hermes Agent Evolution

## Durable lesson

For `~/.hermes/hermes-agent` local evolution work, the user authorizes autonomous **local Git commits** as savepoints. A local commit is a private rollback snapshot, not an official submission.

## Required distinction

- Allowed by default when validated and low-risk: `git commit` in the local checkout.
- Forbidden unless explicitly authorized: `git push`, PR creation, upstream/official submission, publishing, or any external synchronization.
- Use Chinese wording carefully: say “本地快照 / 本地保存点 / local commit（本地提交）”, not “提交官方”.

## When to commit

Commit directly without asking again when all are true:

1. Files are in the active `~/.hermes/hermes-agent` checkout.
2. The batch is verified by targeted tests, import smoke, `git diff --check`, or an equivalent evidence gate.
3. The staged file list is exact and excludes unrelated workspace reports, cache, pycache, desktop outputs, and other task residue.
4. The commit is local-only and no push/PR step follows.

## Batch pattern

For large mixed workspaces:

1. Separate candidates by risk and coherence:
   - tested independent modules,
   - paired phase source+tests,
   - support runtime modules with smoke tests,
   - documentation/governance updates,
   - HOLD core runtime patches.
2. Run focused tests per candidate.
3. `git add -- <exact files>` only.
4. Read back `git diff --cached --name-only` before commit.
5. Commit with a narrow message.
6. Verify `git status --porcelain` and continue the next safe batch.

## HOLD rule

Core runtime or irreversible changes may be committed locally only after rollback evidence and targeted tests exist. Do not push them. If semantic risk remains unresolved, leave them HOLD even if rollback patches exist.

## Report wording

Final report should state:

```text
本地 commit 已保存。
未 push。
未提交官方。
工作区状态: clean / not clean。
HEAD: <short sha>。
```

Do not ask the user for permission to create local commits in this repo merely because commits are involved; ask only before push/PR/official submission or destructive cleanup.
