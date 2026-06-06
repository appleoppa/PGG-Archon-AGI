---
name: pgg-archon-file-archive-governance
description: PGG Archon AGI workspace 文件/档案治理：GitHub 开源规范吸收、六类分区、档案 manifest、引用审计和清理验证。
version: 1.0.0
created: 2026-06-01
---

# PGG Archon File Archive Governance — Compact

## Trigger

Use for workspace/file cleanup, archive manifests, citation/reference audit, GitHub-style project organization and preventing root/Desktop pollution.

## Workflow

1. Inventory files and classify: source, report, evidence, archive, temp, output.
2. Preserve before deleting.
3. Move artifacts to correct workspace/category.
4. Maintain manifest/path/hash where needed.
5. Verify active references before pruning.
6. For large mixed PGG Archon / Hermes Agent workspaces, create an evidence pack before any destructive or commit action: manifest, governance report, verification JSON, readback hashes, targeted tests, and phase-batch triage. See `references/workspace-governance-evidence-pack.md`.
7. For GitHub mirror/resume jobs, do not trust process exit code or push logs alone. Read back source and destination refs with `git ls-remote --heads --tags`, compare ref names and SHAs, distinguish exact `PASS` from `PASS_WITH_EXTRA_DEST_REFS`, and avoid destructive prune cleanup unless explicitly requested. See `references/github-mirror-resume-verification.md`.
8. For large mixed uncommitted workspaces, process by explicit candidate batches: independent modules, core runtime HOLD files, and phase backlogs must not be mixed. Require source+test mapping, targeted tests, `git add --dry-run`, empty-stage readback, and rollback evidence before any irreversible action. See `references/mixed-workspace-batching-and-rollback.md`.
9. For Home / workspace / `.hermes` root治理, roots are not dumping grounds: keep only entrypoints, runtime state, and first-class asset directories. Even "current authority" files must move into governance/spec directories with root files acting only as indexes. See `references/hermes-home-and-workspace-governance-20260601.md`.
10. Before final report, repeat noise cleanup after smoke tests because Python runs may recreate `__pycache__`: `.DS_Store`, non-venv/non-node_modules `*.pyc`, and non-venv/non-node_modules `__pycache__/` should verify as zero unless explicitly exempted.
11. When the user asks whether rules are "固化进系统核心", do not treat governance files or skill updates as sufficient. Distinguish governance artifacts, skill reuse, prompt/context core (`SOUL.md` + relevant `AGENTS.md`), and tool-level hard guards; verify prompt loading before claiming core solidification. See `references/core-solidification-vs-governance-files.md`.
12. For `~/.hermes/hermes-agent` evolution work, local Git commits are authorized savepoints when the batch is verified and staged exactly. Do not ask merely to commit locally; never push/PR/submit official without explicit authorization. See `references/local-git-snapshot-discipline.md`.

## Boundary

Do not delete unverified files or sync to Desktop without explicit user authorization.

## Reference

Full archive governance archived at `references/full-skill-archive-20260601.md`.

Home root directory治理补充模式见 `references/home-root-governance-20260601.md`：区分 runtime/cache/session/tool state 与业务散落目录；外部 repo、测试残留、案件档案迁入 workspace；迁移前生成 manifest，迁移后修复活跃绝对路径引用并排除证据文件自命中。
