# Workspace Governance Evidence Pack Pattern

Use when a PGG Archon / Hermes Agent workspace has many mixed modified and untracked files and the user asks to execute cleanup/governance immediately.

## Pattern

1. Inventory first with `git status --porcelain`, but do not delete, stage, commit, or sync to Desktop during the first pass.
2. Classify paths by durable classes:
   - `source`: `agent/`, `tools/`, `run_agent.py`, `mcp_serve.py`, governing docs.
   - `test`: `tests/`.
   - `workspace_artifact`: `workspace/` reports and generated evidence.
   - `script`: helper scripts.
   - `report_or_data`: JSON/MD/data files outside source/test.
   - `other`: anything requiring human/semantic review.
3. Assign risk classes:
   - `core_or_tooling_review_required`: main loop, MCP, tools, runtime hooks.
   - `review_untracked`: untracked source/test artifacts.
   - `low_artifact`: workspace evidence files.
   - `medium`: modified non-core items.
4. Create a timestamped evidence directory under the correct workspace, not Desktop.
5. Write at least:
   - `workspace_change_manifest.json`
   - `workspace_governance_report.md`
   - `workspace_governance_verification.json`
6. Verify before reporting:
   - selected core AGI/legal modules import using the repo venv.
   - targeted tests pass.
   - `git diff --check` passes.
   - generated files can be read back and have size/SHA256 recorded.
7. For phase-heavy workspaces, add a phase triage by ranges, e.g. `1-50`, `51-100`, `101-150`, `151-200`, `201-250`.
8. Explain that final `git status` count may increase because the evidence pack itself is new. Distinguish inventory count from final count including governance artifacts.

## Boundaries

- Do not delete files merely because they are untracked.
- Do not batch commit core/tooling changes with phase artifacts.
- Do not sync to Desktop unless explicitly authorized.
- Treat `run_agent.py`, `mcp_serve.py`, `tools/*`, runtime hooks, and provider/model paths as requiring separate semantic diff review.

## Pitfalls

- Shell pipelines such as `find ... | xargs ...` can fail on large path sets; use a small Python readback script for per-file size/hash verification.
- A failed convenience command does not invalidate the governance result if a safer readback path succeeds; record the retry pattern, not the transient failure.
