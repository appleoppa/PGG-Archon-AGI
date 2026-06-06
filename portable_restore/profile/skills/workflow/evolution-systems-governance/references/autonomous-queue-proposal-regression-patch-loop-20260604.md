# Autonomous queue → proposal → regression → patch-candidate loop pattern (2026-06-04)

## Trigger

Use when the user asks to push PGG Archon / Hermes toward AGI with autonomous background evolution, especially after `failed-example queue` and `proposal worker` capabilities exist.

## User correction captured

Before implementing more evolution modules, first show a compact but real system-state panel:

- EVOLUTION_MANIFEST last_updated / capability keys / latest audits.
- Current git HEAD and recent commits.
- Key PGG modules importability and focused tests.
- Rust fused watcher / launchd status.
- Existing cron jobs, especially paused legacy ARS/autopromote jobs.
- Existing queue/proposal/regression artifacts.

Do not start adding modules until this proves the new work is not duplicating already-finished work.

## Formula-guided sequence

Use APEX / PGG formula as a gap map, not decoration:

```text
APEX_Ultimate = Ω_A · α_ack · β_bg · ΨΛΓΞΦΥ · EVM · A · B · TDHLGWB - ΣΔ_all
```

Typical ΣΔ_all gaps for this class:

1. no automated regression generator from proposal yet
2. no patch candidate sandbox yet
3. no verified GeneDB promotion from regression outcomes yet
4. provider-audit channel failure / empty visible output

Close only what is actually implemented and verified.

## Real multi-LLM gate

Call configured providers with a compact evidence payload:

- GPT / Claude via Responses API or codex_responses-compatible `/responses`.
- DeepSeek / MiniMax via chat_completions.
- Record provider, model, status, HTTP status, visible_output_chars, path, sha256.
- If a provider returns empty output, HTTP 403, 502, or exhausted accounts, report that exactly; do not count it as effective advice.

The output should identify the highest-ROI next gap and verification requirements.

## Implementation ladder

Proceed one rung at a time, with tests and manifest readback after each:

1. `failed-example queue v2`
   - replayable JSONL records with prompt, scorer, expected, prediction, score_delta, priority, input_hash, promotion_gate.
   - read-only prioritized consumer.

2. `proposal worker`
   - queue item → read-only proposal with repair_focus, proposed_actions, verification_plan.
   - CLI entrypoint for cron/watcher use.

3. `targeted regression generator`
   - proposal + source queue item → deterministic `BenchmarkTask` JSONL / regression fixture.
   - prove old failure prediction fails and truthful repair passes.

4. `patch candidate sandbox`
   - regression fixture → read-only patch-candidate plan with target_surfaces, patch steps, verification commands, risk, promotion gate.
   - no file edits at this stage.

5. `patch application sandbox` (next rung; higher risk)
   - isolated worktree / temp copy only.
   - apply candidate patch, run commands, classify PASS/WATCH/BLOCKED.
   - only PASS can move toward manifest/GeneDB candidate gate.

## Background loop pattern

Avoid duplicating Rust fused-watch or old ARS/autopromote cron. Add a no-agent Hermes cron only for the missing rung, e.g. a script that scans new queue files and writes evidence:

```text
queue → proposal → targeted_regression → patch_candidate
```

Script discipline:

- use sha256 state to avoid reprocessing the same queue.
- write state under `~/.hermes/data/pgg-background-evolution/`.
- append JSONL ledger cycles.
- stay silent when there is no new work and no errors.
- print JSON only when new proposals/regressions/candidates are generated or when an error occurs.
- compile-check every module it invokes.

## Verification bundle

Minimum proof before claiming completion:

- focused pytest for all touched modules.
- `py_compile` for all invoked modules.
- CLI smoke on real queue/proposal/fixture artifacts.
- background-loop smoke on a new test queue showing counts for every stage.
- dedupe smoke showing second run generates nothing.
- EVOLUTION_MANIFEST update + readback sha256.
- scoped commit for repo files only; workspace reports/scripts/manifests usually remain outside repo unless explicitly tracked.

## Boundaries

Do not call this full AGI. Use `PASS_WITH_BOUNDARY` for background automation that stops before patch application or GeneDB writes. Do not auto-restore legacy ARS/autopromote jobs when Rust fused-watch is the active runtime.
