# 2026-06-02 CodeGenesis WATCH triage: truncation false positives and metric noise

## Session signal

During a PGG Archon/AGI continuation loop, the user repeatedly said “继续” / “怎么停了，继续”. Treat this as a workflow correction: do not pause after partial diagnosis when the next step is low-risk, reversible, and already above the user's >75 continuation threshold. Close the loop with edit → targeted tests → health check → `EVOLUTION_MANIFEST` update → scoped commit → concise evidence report.

## Durable technique

CodeGenesis reported WATCH with apparent syntax errors:

- `gateway/run.py:6585:'[' was never closed`
- `hermes_cli/auth.py:7594:'(' was never closed`

Direct `py_compile gateway/run.py hermes_cli/auth.py` passed. Root cause was scanner-side truncation: `_safe_bytes()` read only the first 300 KB, then `ast.parse()` saw incomplete large files and emitted false SyntaxError reports.

Fix pattern:

1. Before editing core files, verify suspected syntax errors with `python -m py_compile <file>`.
2. If py_compile passes but scanner reports SyntaxError, inspect scanner read limits/truncation logic.
3. Raise bounded read cap enough for normal large in-tree modules rather than switching to unbounded reads.
4. Add regression test with a syntactically valid large Python file so future scanners do not reintroduce truncation false positives.
5. Re-run scanner and expect `parsed_count == py_count` and `parse_errors == 0` before moving on to remaining WATCH metrics.

Concrete successful patch from this session:

- `_safe_bytes` cap raised from `300_000` to `2_000_000` bytes.
- Regression test added: `test_scanner_does_not_truncate_large_valid_python_file`.
- Verification: scanner parsed 600/600 files, parse_errors 0, tests 6 passed, APEX-GOD health 21/21 PASS.

## Remaining WATCH metric lesson

After truncation fix, WATCH remained due to:

- `high_duplication`
- `low_test_ratio`

Top duplicate samples were low-information syntax shell lines such as `)`, `try:`, and `"""`. Future duplicate metrics should filter low-information structural lines or weight by semantic content before using duplication as a quality blocker.

The test ratio metric was also too naive: test file count / Python file count can understate coverage in large repos. Prefer module/directory coverage or executable targeted-test evidence for AGI readiness decisions.
