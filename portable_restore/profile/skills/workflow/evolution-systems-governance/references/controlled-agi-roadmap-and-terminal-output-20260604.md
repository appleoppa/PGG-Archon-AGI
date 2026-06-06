# Controlled AGI Roadmap + Terminal Output Pattern — 2026-06-04

## Trigger

Use this reference when the user asks to continue PGG Archon / AGI evolution strictly according to plan, prevent disruptive detours, or keep moving after a blocker while preserving truth gates.

Typical user signals:

- “请严格按照AGI计划一步步有计划推进”
- “杜绝中间被扰乱或者破坏性流程”
- “自行解决卡点，继续执行”
- “调用 DeepSeek / MiniMax / GPT 代入公式，不造假解决”
- Feedback that terminal output should be more compact and readable.

## Core operating rule

Treat the AGI roadmap as a controlled sequence, not an open-ended brainstorm. At every stage:

1. Read current state first: status dashboard, manifest, git status, active watcher/cron state.
2. Advance exactly one roadmap component.
3. If a command fails, stop the stage, isolate the failure with smaller commands, fix it, and rerun.
4. Do not jump to the next component until tests, smoke, manifest/report and scoped commit close the current one.
5. Do not perform destructive steps: no automatic main patch, GeneDB promotion, launchd replacement, scheduler/security boundary edits, or overlay restoration unless explicitly authorized and separately gated.

## Roadmap sequence used in this session

```text
P0  producer automation verification
P1  main patch gate module
P2  LLM quorum gate module
P3  Rust/Python event ledger side-channel
P4  open-source targeted absorption only when a real blocker appears
```

## P0 acceptance pattern — producer automation verification

Goal: prove the existing benchmark producer creates a real `*.evolution_queue.jsonl`, and the autonomous loop consumes it through readiness.

Verified pattern:

1. Use existing producer, not a handwritten fake queue:
   - `agent.pgg_archon_benchmark_loop.run_integrated_benchmark(...)`
   - sample failing prediction allowed for controlled smoke.
2. Confirm queue facts:
   - queue path exists
   - line count > 0
   - first item has schema `PGGArchonEvolutionQueueItem/v2`
   - queue sha256 recorded
3. Run `~/.hermes/scripts/pgg_autonomous_evolution_loop.py`.
4. Read latest ledger cycle and require:
   - `status=PASS`
   - `generated_count>=1`
   - `error_count=0`
   - proposal/regression/patch_candidate/sandbox/patch_apply present
   - promotion readiness status `READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW`
5. Update `EVOLUTION_MANIFEST.json`, write report, and only then advance.

## P1 acceptance pattern — main patch gate module

Goal: add a read-only gate that decides whether a readiness package may proceed to dry-run/main-patch review.

Module pattern:

- Reads `promotion_readiness_package.json`.
- Checks:
  - package status is ready
  - package blockers are empty
  - patch diff exists and is non-empty
  - diff target files are parsed
  - target files are within allowlist such as `tests/fixtures/` or `tests/`
  - readiness package confirms patch apply and regression tasks
- Outputs `READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW` or `BLOCKED_MAIN_PATCH_GATE`.
- Must not apply patch, commit, or write GeneDB.

Testing pattern:

- READY allowed test fixture target.
- BLOCKED disallowed target such as `agent/core_security.py`.
- BLOCKED non-ready package.
- CLI writes result.
- Real dry-run against latest readiness package.

## P2 acceptance pattern — LLM quorum gate module

Goal: module-ize saved-evidence quorum review without making live provider calls.

Module pattern:

- Inputs one or more saved model evidence JSON files.
- Normalizes provider/model/status/visible chars/classified verdict.
- Counts only `status=ok_visible`, `visible_output_chars>0`, `classified_verdict=PASS` as pass.
- Outputs `PASS_QUORUM` or `BLOCKED_QUORUM` based on configurable `required_pass_count`.
- Must not call providers, promote GeneDB, or apply patches.

Testing pattern:

- 2/3 PASS succeeds.
- 1/3 PASS blocks.
- CLI writes result.
- Real B-fallback evidence can be used as smoke when available, but do not hardcode its paths into the module.

## P3 acceptance pattern — Rust/Python event ledger side-channel

Goal: create an append-only JSONL event ledger shared by Python autonomous loop and Rust fused watcher observer without replacing runtime services.

Module pattern:

- `PGGAutonomousEvolutionEvent/v1`
- append-only ledger path, e.g. `~/.hermes/data/pgg-background-evolution/autonomous_events.jsonl`
- functions:
  - build event
  - append event
  - load recent events
  - summarize events
  - observe Rust watcher via `launchctl print gui/501/ai.hermes.evol-watcher`
- Boundary: side-channel only; no launchd replacement, no GeneDB mutation.

Testing pattern:

- append/load/summary.
- CLI append/summary.
- mock Rust watcher observer in unit tests.
- real smoke appends one Python loop event and one Rust watcher observer event, then reads summary.

## Handling tool/command failures

Do not treat an empty combined-command output as proof of failure cause. Split the failing chain:

1. Run the unit test alone with `-vv`.
2. Run the real smoke command alone.
3. Run `py_compile` alone.
4. Run `git diff --check` alone.
5. Only after all pass, re-run the grouped regression.

Lesson: the durable pattern is not “tool is broken”; it is “decompose combined validation chains and capture RC per step before changing code.”

## Terminal output style for this user

Use compact terminal-readable status blocks instead of wide tables.

Preferred shape:

```text
状态
- 路线：AGI controlled roadmap
- 本轮：P2 LLM quorum gate
- 结果：PASS
- 测试：55 passed
- 提交：92c10030a

进度
P0  producer 自动化核验       PASS
P1  main patch gate 模块化    PASS
P2  LLM quorum gate 模块化    PASS
P3  Rust/Python event ledger  NEXT

边界
- no main patch
- no GeneDB mutation
- no full AGI claim
```

Avoid large wide tables in terminal because line wrapping reduces readability.

## Reporting checklist

At the end of each component report:

- status
- module/files changed
- tests count
- real smoke evidence
- manifest sha256
- report path
- commit hash if code changed
- explicit boundary and next component

## Anti-overclaim boundary

This roadmap improves a bounded autonomous engineering loop. It is not evidence of full AGI, zero risk, legal correctness, or unsupervised production autonomy.
