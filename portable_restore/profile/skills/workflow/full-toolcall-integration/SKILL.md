---
name: full-toolcall-integration
description: 将复杂任务一次性拆成全局轨迹，识别依赖、工具、风险、并行点，并用读回验证形成可交付闭环。
version: 1.0.0
category: workflow
tags: [超级进化5.5, 全局轨迹, 并行调度, 负载均衡]
created: 2026-05-25
updated: 2026-05-25
---

# Full Toolcall Integration — Compact

## Trigger

Use for complex tasks requiring multiple tools, dependency ordering, parallelizable checks, risk control and evidence-backed final delivery.

## Workflow

1. Build global trajectory: goal, dependencies, tools, risks, verification.
2. Run prerequisite discovery first.
3. Parallelize independent checks when safe.
4. Execute changes with rollback path.
5. Verify every claimed result with real output/readback.
6. Summarize only evidence, not raw logs.

## Sidecar phase chains

For multi-phase sidecar chains, a phase implementation is not complete until the CLI/wrapper path can run it, compact stdout exposes its status/report/gene_id, and the generated report plus DB/GeneDB readback have been verified. Keep wrapper scripts aligned with the highest safe phase; otherwise later evidence gates may correctly block on stale wrapper flags. See `references/sidecar-phase-cli-cron-extension.md`.

## Reference

Full trajectory templates archived at `references/full-skill-archive-20260601.md`.
Additional pattern: `references/sidecar-phase-cli-cron-extension.md`.
Private GitHub mirror + local deployment + GPT audit evidence pattern: `references/private-repo-local-deploy-gpt-audit.md`.
Local ML repo deployment smoke-test pattern: `references/local-ml-repo-deploy-smoke-test.md`.
Multi-LLM parallel smoke + budget pattern: `references/multi-llm-parallel-smoke-budget-20260604.md`.

## Background process pitfalls (added 2026-06-04)

1. **`terminal(background=true)` does NOT propagate `cd` to sys.path.** When
   running a Python script from `/tmp` that imports from a package
   (e.g. `from agent.foo import ...`), `cd $REPO && python3 /tmp/x.py`
   fails with `ModuleNotFoundError: No module named 'agent'`. **Fix**:
   pass `PYTHONPATH` explicitly, e.g.
   `cd $REPO && PYTHONPATH=$REPO python3 /tmp/x.py`, or run the script
   as a module via `python3 -m agent.x`. This applies to **every**
   background Python invocation that imports a package.

2. **Max tool-calling iterations cap is the real wall clock for
   long batches.** A 4-LLM × 33-file batch (~132 LLM calls) hit the
   cap mid-run on 2026-06-04 while polling `process.poll` repeatedly.
   Each `process.poll` burns one iteration. **Fix**: launch the long
   batch as ONE `terminal(background=true, notify_on_complete=true)`
   call, then in the same turn use at most one `process.list` (single
   iteration) to check liveness. The `notify_on_complete` callback
   wakes the next turn; do not poll in a loop within the same turn.
   Plan the current turn to land only the launcher + supporting
   `write_file` of the verifier script, not the foreground wait.

3. **Heredoc + `re.sub` with `$` still gets eaten by bash even with
   `<<'PY'`.** Confirmed 2026-06-04: `re.sub(r"^```(?:json)?\s*", ...)`
   inside `<<'PY' ... PY` produces `bad substitution: no closing "`" in
   $` errors. **Fix**: write the script with `skill_manage` to
   `references/` / `templates/` / `scripts/` (or `write_file` when
   allowed) and run `python3 <path>`. Never embed `re.sub` regex with
   `$` in a heredoc.

4. **`terminal(...)` with shell-level background wrappers
   (`nohup` / `disown` / `setsid` / trailing `&`)** is rejected with
   `Foreground command uses shell-level background wrappers`. **Fix**:
   use `terminal(background=true, ...)` and let Hermes track the
   process. Do NOT add `nohup` / `disown`.
