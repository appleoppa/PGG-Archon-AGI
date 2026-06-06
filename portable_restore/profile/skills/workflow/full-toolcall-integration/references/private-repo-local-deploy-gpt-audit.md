# Private repo → local deploy → GPT audit evidence pattern

Use this reference when a user asks to download/mirror a GitHub project, deploy it locally, and run an external-model audit.

## Durable workflow

1. Mirror and preserve provenance
   - Clone source repo locally in a clean workspace.
   - Create or reuse the user's private GitHub repo.
   - Push all relevant refs/tags.
   - Read back `isPrivate`, URL, local HEAD and remote HEAD before claiming completion.

2. Local deployment is not just cloning
   - Inspect project metadata and tests.
   - Create an isolated environment.
   - Install in editable/local mode when appropriate.
   - Run tests and a minimal runtime smoke test.
   - If low-risk deployment blockers are found, fix them, rerun tests, and push only the files touched in this task.

3. Full audit evidence pack
   - Generate an inventory: tracked files, code line counts, git status, dependency metadata.
   - Run local checks: test suite, syntax/compile check, dependency consistency, security scanners, lint.
   - Produce compact machine-readable evidence files under a project-local `audit_reports/` or equivalent directory.

4. External GPT/Claude audit call
   - For GPT/Claude providers configured as `codex_responses`, call `/v1/responses`, not `/v1/chat/completions`.
   - Use payload shape: `model`, `input`, `instructions`, `max_output_tokens`.
   - Preserve raw JSON response and extract the report to a readable Markdown file.

5. If the external model disconnects on a large evidence pack
   - Do not treat it as model failure immediately.
   - First retry with a smaller, structured evidence pack: summary counts, tool highlights, selected source snippets, and top risks.
   - Keep the lesson as “compact and retry”, not “provider is broken”.

6. Final verification
   - Rerun tests after any low-risk fix.
   - If audit found an obvious reversible fix, apply it and verify.
   - Commit/push only the current task's files.
   - Final reply should include: local path, private repo URL/status, model call status, test result, report paths, remote HEAD.

## Pitfalls

- Do not say “deployed locally” if the repository was only cloned.
- Do not claim GPT/Claude participation without a real provider/API response and saved evidence.
- Avoid dumping raw scanner logs into the user reply; save logs to files and summarize findings.
- Large prompt uploads to Responses API may close the connection; compact evidence and retry before escalating.
