# CodeGenesis Progressive Observability Pattern — 2026-06-02

## Context

During a PGG Archon evolution loop, the CodeGenesis scanner initially surfaced coarse `high_duplication` warnings and earlier parse-error false positives caused by bounded file truncation. The useful durable lesson is the progressive observability pattern, not the one-off repository numbers.

## Pattern

When a quality scanner finds a broad warning such as `high_duplication`, do not immediately refactor core business/runtime files. First make the scanner itself more explanatory and keep it read-only.

Progressive layers that worked well:

1. Syntax confidence
   - Keep bounded reads, but set the bound high enough for large generated/runtime files.
   - Verify suspected syntax errors with direct `py_compile` before claiming real parse failures.
   - Report `parse_errors=0` or concrete `file:line:message` samples.

2. Duplicate signal hygiene
   - Filter low-information syntax shell lines before computing duplicate rate.
   - Examples: braces/brackets/parentheses-only lines, `try:`, `else:`, `finally:`, bare triple quotes, `pass`, `return`, `continue`, `break`.
   - Keep the filter conservative; do not hide semantically meaningful repeated lines.

3. Pattern summary
   - Add grouped summaries such as defensive exceptions, `return None`, boolean returns, empty prints, and `other`.
   - This separates acceptable defensive repetition from possible abstraction candidates.

4. Directory summary
   - Aggregate repeated signal lines by top-level directory/module.
   - Use this to pick review targets without editing business code.

5. File summary
   - Aggregate by file to identify concrete hotspots.
   - Keep output bounded, e.g. top 15.

6. AST hotspot summary
   - Parse AST and rank large/branchy functions by lines and branch count.
   - Useful thresholds from the session: function branches >= 8 or function lines >= 160 for hotspot collection; rank by branch count then line count.

7. AST slice summary
   - Convert hotspots into read-only phase hints before any refactor.
   - Example hints:
     - `extract_stage_pipeline` for very large functions.
     - `split_branch_cluster` for high branch density.
     - `review_local_helper_extraction` for smaller local helper candidates.
   - Include `slice_count_hint` and evidence such as `N lines / M branches`.

## Guardrails

- Scanner improvements are additive observability, not production-readiness claims.
- Do not modify Hermes core scheduler, prompt/cache lifecycle, or security boundary as part of a scanner metric loop.
- Do not refactor large runtime functions solely because a metric is high. First produce read-only phase boundaries, state variables, tool-call points, exception clusters, and test seams.
- Stage only scanner/test files in commits; do not mix unrelated workspace changes.

## Verification loop

For each scanner enhancement:

1. Add or update targeted scanner tests.
2. Run targeted pytest.
3. Run `py_compile` for edited Python files.
4. Run `git diff --check`.
5. Run the PGG/APEX health check if the scanner feeds evolution gates.
6. Update `EVOLUTION_MANIFEST.json` when it is part of the evolution evidence chain.
7. Commit only the current scanner/test changes.
8. Write a concise evidence report under the workspace evidence area.

## Reusable schema fields

Useful fields added in the session:

- `top_duplicate_lines`
- `duplicate_pattern_summary`
- `duplicate_directory_summary`
- `duplicate_file_summary`
- `ast_hotspot_summary`
- `ast_slice_summary`

These are class-level ideas: future scanners should expose a path from broad warning → grouped signal → concrete review target → safe, testable next step.
