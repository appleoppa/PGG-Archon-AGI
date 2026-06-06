# P1 MiMo audited manifest gate closure — 2026-06-06

## Closed-loop shape

```text
LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle
```

## What happened

A manifest gate initially allowed a local deterministic precheck path to behave like an external MiMo audit success. Multi-LLM review identified that trusting a top-level `pass_count` was insufficient; the gate must recompute eligibility from per-result rows.

## Durable pattern

1. **LDR(K)**: External eval/judge patterns support an unavailable/abstain/local-precheck state that must not count as pass. If GitHub search API is unavailable, record that honestly and use accessible raw docs or existing references without pretending full search succeeded.
2. **GapDetect**: Identify not only primary logic bugs, but also review-pack and commit-dependency gaps:
   - untracked files can make `git diff` empty;
   - dirty worktree can hide missing imports in a committed file.
3. **CodeSelfFix**:
   - add `judge_called`;
   - set local-only `audit_verdict=None`;
   - recompute `eligible_pass_count` from rows where `status == OK_PARSED` and `audit_verdict == PASS`;
   - non-zero provider exit remains `ERROR` even with parseable stdout.
4. **HotReload/TaskSolve**:
   - focused pytest;
   - py_compile;
   - CLI no-judge smoke must produce WATCH;
   - import smoke from committed dependency graph.
5. **KnowledgeSettle**:
   - scoped commit for the gate;
   - scoped follow-up commit for missed dependency if discovered;
   - manifest entry with readback;
   - LLM review summary that records timeout/error channels honestly.

## Review discipline

If a multi-LLM reviewer gives WATCH because the review pack is incomplete, do not overrule it. Create a targeted prompt with the complete missing functions and re-run the reviewer. If a provider times out but emits parseable JSON, keep the raw text as evidence but effective verdict is ERROR until a clean exit-0 rerun succeeds.

## Boundary

Internal engineering closure only. It does not prove legal correctness, official benchmark performance, or AGI level.
