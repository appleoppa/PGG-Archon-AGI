# MiMo / Agnes third-party judge role update — 2026-06-06

## Durable rule

MiMo (`mimo_v25_pro_auditor`) is the fixed third-party benchmark/audit judge for PGG Archon multi-LLM evaluation. It should be excluded from ordinary processing pools.

Agnes (`agnes_ai`) is no longer the fixed third-party judge because its link is unstable. It may be used as an ordinary/non-critical collaboration channel, but failures must be recorded honestly as `ERROR`/`UNKNOWN` and must not block or be converted into PASS.

## Why this matters

A later session may see diffs that appear to move MiMo out of default providers and put Agnes into ordinary pools. That is intentional under the new rule. Do not “fix” it back to the old rule without checking cross-session context.

## Verification pattern

When touching provider role code/tests, assert all of the following:

```text
default/ordinary provider pools exclude mimo_v25_pro_auditor
third_party_benchmark_judge_providers() returns mimo_v25_pro_auditor
processing LLM pools exclude label mimo
third-party judge pools include label mimo
Agnes may be present in ordinary/non-critical pools
Agnes failures are surfaced honestly as ERROR/UNKNOWN
```

## Pitfall from session

The assistant initially treated the MiMo/Agnes swap as a bug because older memory said Agnes was third-party judge. The user corrected that the swap had been made in another session due to Agnes instability. Future sessions must use `session_search` or current memory before reversing provider-role changes.
