# MiMo manifest gate PASS eligibility hardening — 2026-06-06

## Trigger

Use when adding or reviewing a manifest/audit gate that claims `PASS` based on an LLM judge, especially MiMo as held-out third-party audit/benchmark judge.

## Core lesson

A manifest gate must not trust a top-level `pass_count` or a local deterministic precheck as proof of external judge success.

`PASS` is allowed only when every required judge result is both:

```text
status == OK_PARSED
and
audit_verdict == PASS
```

and the external judge was actually called:

```text
judge_called == true
```

Everything else is `WATCH` / `ERROR`, including:

```text
--no-mimo
LOCAL_PRECHECK_ONLY
OK_UNPARSED
ERROR
UNAVAILABLE_TIMEOUT
subprocess returncode != 0
missing judge_called
reported pass_count != recomputed eligible_pass_count
```

## Implementation pattern

1. Record `judge_called` in the audit summary.
2. For local precheck/no-judge paths, write `status=LOCAL_PRECHECK_ONLY` and `audit_verdict=None`.
3. Recompute `eligible_pass_count` from per-result rows inside the manifest gate:

```python
eligible_pass_count = sum(
    1
    for r in results
    if isinstance(r, dict)
    and r.get("status") == "OK_PARSED"
    and r.get("audit_verdict") == "PASS"
)
```

4. Add downgrade reasons for:
   - `mimo_judge_not_called`
   - `reported_pass_count_mismatch=<reported>_vs_eligible_<eligible>`
   - `eligible_audit_pass_count=<eligible>_of_<len(results)>`
   - `audit_timeout_count=<n>`
5. In provider-call wrappers, treat non-zero subprocess exit as `ERROR` even if stdout contains parseable JSON. Parsed text from a timed-out/non-zero call is not a clean PASS.
6. CLI status should use the same rule:

```python
cli_status = "PASS" if summary.judge_called and summary.pass_count == len(summary.results) else "WATCH"
```

## Tests to include

- `judge_called=False` with all local prechecks must be `WATCH`.
- `results=[{}]` plus forged `pass_count=1` must be `WATCH`.
- `LOCAL_PRECHECK_ONLY + audit_verdict=PASS` must still be `WATCH`.
- `OK_UNPARSED + audit_verdict=PASS` must still be `WATCH`.
- only all `OK_PARSED/PASS` rows can be `PASS`.
- `--no-mimo` CLI smoke must output `WATCH`.
- import smoke after commit must pass from committed dependencies, not just dirty worktree.

## Review-pack pitfall

For new untracked files, `git diff` may be empty. A multi-LLM review pack must include full file contents or staged diff after `git add -N`/staging. Do not send an empty diff to LLM reviewers.

## Multi-LLM truthfulness pitfall

If an LLM call times out or exits non-zero but leaves parseable JSON in stdout, record the parse as raw evidence only. Effective verdict remains `ERROR` unless the process exit code is zero.

## Commit dependency pitfall

After committing a new module, check imports against committed files. If a committed file imports an untracked dependency, either commit the dependency in a scoped follow-up or make the import optional. Do not leave a commit that only works because the dirty worktree contains extra files.

## Boundary

This is an internal engineering anti-overclaim gate. It is not legal correctness proof, not an official benchmark score, and not AGI level proof.
