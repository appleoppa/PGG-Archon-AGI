# Workspace Storage Governance & Cleanup Pattern

Use this pattern when the user asks to review, integrate, adjust, or clean `~/.hermes/workspace` files.

## Trigger

- “查看并分析工作空间的文件和文件储存规则”
- “整合并调整文件存放”
- “过期、冗余文件删除”
- User frustration such as “怎么又停了” during a cleanup or implementation task: do not pause at analysis; continue to low-risk verified actions.

## Workflow

1. **Load governance skill and create a todo.** Treat the task as an execution task, not a report-only audit.
2. **Read-only inventory first.** Generate a compact audit under `workspace/审计队列/workspace_governance_<date>/` with:
   - top-level size/file counts;
   - root stray files;
   - `.DS_Store`, `*.pyc`, `__pycache__`, empty temp dirs;
   - large files;
   - duplicate candidates only in safe generated/audit areas;
   - protected directories such as `智库/`, active legal KB catalog, case libraries, governance files.
3. **Write/update storage rules.** Put durable rules in `workspace/治理/WORKSPACE_STORAGE_RULES.md` and update active/archive indexes if paths change.
4. **Safe cleanup tiers.**
   - Direct delete: `.DS_Store`, `*.pyc`, `__pycache__`, empty top-level temp dirs (`tmp`, `tmp_extract`, `repos`, `repo_compare`, `external_repos`, `github_repos`) when empty.
   - Move/organize: root process reports into `reports/<domain>/`, historical state into `recovery/`, historical heartbeat/log notes into `监控日志/`.
   - Compress then delete raw historical repair dirs when they are already marked archive-only, e.g. `session_repair_backup`, `session_repair_archive`, `session_repair_archive_sqlite_visible` → `治理/历史归档/<name>.tar.gz`.
   - Delete replaced legacy stores only after validation, e.g. old Chroma legacy under `法律知识向量库/99_legacy_chroma_readonly/` after current `catalog.sqlite3`, pipelines, regressions, and native tool smoke tests pass.
5. **Do not delete by emptiness alone in business structures.** Case-library directories and department workflow folders may be valid placeholders even if empty.
6. **Verify after cleanup.** Check:
   - `.DS_Store`, `*.pyc`, `__pycache__` counts;
   - protected assets still exist;
   - SQLite `pragma integrity_check` for active DBs;
   - domain smoke test if a cleaned area supports an active toolchain;
   - gateway/runtime still loaded if relevant.
7. **Handle macOS Finder noise.** Finder may regenerate `.DS_Store` during verification. If it reappears, delete again immediately and report that it is regenerable noise, not a business failure.
8. **Write final evidence.** Save:
   - `WORKSPACE_AUDIT_BEFORE.json`;
   - `WORKSPACE_CLEANUP_ACTIONS.json`;
   - `WORKSPACE_VERIFY_AFTER.json`;
   - `WORKSPACE_GOVERNANCE_SUMMARY.json`;
   - a concise Markdown report.

## User preference embedded

When the user complains that the agent “stopped” mid-task, the correct response for this class of task is to continue executing the next safe, reversible, evidence-backed step immediately. Do not answer with excuses or a plan-only message.

## Reporting

Use compact Chinese fields:

- 状态
- 本轮处理
- 新规则
- 验证结果
- 主要体量
- 证据文件
- 保留风险/后续

Avoid sending files to Desktop unless explicitly requested.
