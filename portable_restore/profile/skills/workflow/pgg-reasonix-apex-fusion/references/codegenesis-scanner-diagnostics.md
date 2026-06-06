# CodeGenesis Scanner Diagnostics Pattern

## Trigger

Use this reference when a PGG Archon / AGI evolution task introduces or tunes a read-only code-quality scanner, especially when the user says "继续" and expects autonomous low-risk closure rather than a plan.

## Durable lessons from the session

1. **Do not stop on user "继续" when the next step is low-risk and reversible.** Continue through implementation, targeted tests, health check, EVOLUTION_MANIFEST update, commit, and a concise evidence report.
2. **Bounded reads can create false SyntaxError reports.** If `ast.parse()` reports syntax errors on large files, first verify the files directly with `py_compile`. A scanner that reads only a truncated prefix can fabricate errors such as "was never closed". Fix the scanner's bounded read cap or record truncation explicitly before blaming the target file.
3. **Expose diagnostic samples, not only aggregate scores.** Quality gates should return actionable evidence fields such as `parse_error_samples` and `top_duplicate_lines` so future runs can locate root causes without rereading the whole repo.
4. **Filter low-information duplicate lines.** Raw duplicate-line metrics are polluted by syntax-shell lines like `)`, `]`, `try:`, `else:`, `finally:`, triple quotes, and bare flow-control statements. Filter these before computing the signal duplication rate.
5. **Avoid file-count-only test ratios under sampling.** If scanning only the first N Python files, `test_files / sampled_files` can undercount tests sorted later. Add a directory/module-level coverage estimate, e.g. count tests under `tests/` and compare against source top-level directories, then combine with the sampled file ratio.
6. **Do not blindly modify core code to make a scanner pass.** If the remaining warning is high duplication, first aggregate by directory/module and classify whether it is defensive boilerplate, adapter repetition, true helper-extraction opportunity, or another scanner-filter issue.

## Verification checklist

- Run the scanner before and after the change and compare `status`, `parse_errors`, `dup_line_rate`, `test_ratio`, and `warnings`.
- Add regression tests for every scanner false-positive class fixed.
- Run targeted pytest, `py_compile` for edited Python files, and `git diff --check`.
- Run the PGG Archon health check after scanner/gate changes.
- Run `python -m apex_god.evolution_manifest --update` and report the manifest hash.
- Commit only the files relevant to the current scanner/gate change; do not mix sibling untracked modules.
