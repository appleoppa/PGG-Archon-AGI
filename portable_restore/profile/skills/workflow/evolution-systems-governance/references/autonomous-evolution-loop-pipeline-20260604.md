# Autonomous Evolution Loop Pipeline — 2026-06-04

## Trigger

Use when the user asks to continue PGG Archon / AGI evolution with “all LLMs”, APEX/SE20 formula substitution, background automation, or full autonomous evolution loops.

## Durable lesson

Do not jump straight to adding another module. First establish a compact verified state panel so the next action is not duplicate work:

- `EVOLUTION_MANIFEST.json`: last_updated, capabilities, latest audits/milestones, 5D score mouth.
- Runtime: Rust `ai.hermes.evol-watcher`, launchd PID, watched paths, logs.
- Repo: HEAD, recent commits, clean/dirty state.
- Existing automation: Hermes cron jobs; especially paused legacy ARS/autopromote jobs vs active Rust fused-watch.
- Existing modules: importability and targeted tests for benchmark, provider health, queue, proposal, regression, patch sandbox surfaces.
- Existing artifacts: queue/proposal/regression/patch candidate JSON paths and ledgers.

Report this panel before implementing if the user challenges whether current system state was really checked.

## Safe autonomous pipeline shape

The verified low-risk pipeline is:

```text
failed-example queue v2
→ read-only proposal worker
→ targeted regression generator
→ read-only patch candidate sandbox
→ patch sandbox readiness
→ temp git worktree patch apply sandbox
→ main worktree apply gate
→ manifest readback
→ GeneDB candidate promotion gate
```

Completed stages may be automated by no-agent cron when they are read-only or confined to temporary worktrees. Main worktree mutation and GeneDB promotion remain gated.

## Module pattern

Prefer small additive modules with CLIs and tests:

- `agent.pgg_archon_evolution_proposal`
- `agent.pgg_archon_regression_generator`
- `agent.pgg_archon_patch_candidate_sandbox`
- `agent.pgg_archon_patch_sandbox`
- `agent.pgg_archon_patch_apply_sandbox`

Each module should have:

- dataclass result schema
- pure builder/evaluator function
- `write_*` function producing JSON + JSONL or result JSON
- `main(argv=None)` CLI
- pytest coverage for function and CLI
- boundary string saying what it does not do

## Background loop script pattern

Use a no-agent script under `~/.hermes/scripts/` for autonomous glue when avoiding LLM/token cost:

- load state from `~/.hermes/data/pgg-background-evolution/autonomous_loop_state.json`
- scan `~/.hermes/workspace/evolution/**/*.evolution_queue.jsonl`
- skip empty queues
- de-duplicate by queue SHA-256
- run module CLIs in order
- append cycles to `~/.hermes/data/pgg-background-evolution/autonomous_loop_cycles.jsonl`
- emit stdout only when new work or errors occur; stay silent when no new work

Cron shape:

```text
name: PGG Archon autonomous queue-to-proposal evolution loop
script: pgg_autonomous_evolution_loop.py
schedule: every 30m
no_agent: true
workdir: ~/.hermes/hermes-agent
```

## Patch apply safety

When a candidate reaches patch application, do not patch the main repo directly. Use temp worktree first:

1. `git worktree add --detach <workspace-path> HEAD`
2. apply the narrow candidate patch inside the worktree
3. for newly-created files, run `git add -N <file>` so `git diff` captures intent-to-add without staging content
4. write `candidate.diff`
5. run candidate `verification_commands`
6. mark `PASS_PATCH_SANDBOX` only when diff is non-empty and all commands pass
7. do not commit or mutate the main worktree

Only after PASS may a later gate review/apply the diff to the main worktree with scoped add/commit.

## Multi-LLM formula audit pattern

When the user asks “调用所有 LLM / 代入公式 / 不造假”:

- Build a compact evidence payload from verified facts, not claims.
- Include APEX formula and explicit `ΣΔ_all` candidate gaps.
- Call GPT/Claude via Responses/codex_responses, DeepSeek/MiniMax via chat_completions as configured.
- Record provider/model/status/http/visible chars/output hash/path.
- If a provider returns empty output, HTTP error, or account exhausted, record it and do not count it as an effective reviewer.
- Implement only the next step that converges across visible outputs and verified local gaps.

## Reporting contract

For each stage, report:

- exact module/script paths
- JSON evidence paths and SHA-256 where available
- tests passed
- smoke result fields (`proposal_count`, `fixture_count`, `candidate_count`, `pass_count`, `status`)
- manifest capability updated/read back
- commit SHA for repo modules
- explicit boundary: not full AGI, no main worktree mutation unless actually done, no GeneDB promotion unless actually written/read back
