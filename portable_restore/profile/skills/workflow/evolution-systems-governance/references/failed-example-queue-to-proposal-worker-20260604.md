# Failed-example Queue → Proposal Worker Pattern (2026-06-04)

## Context

In a PGG Archon / Hermes AGI fast-path session, the user corrected the execution sequence: before implementing an evolution step, the agent must first inspect and report the current system evolution state — core, modules, self-evolution jobs, Rust architecture, runtime watchers, manifest, and git chain. A localized fix without that state panel feels ungrounded even if technically useful.

## Required pre-state audit for AGI/PGG evolution tasks

Before choosing or implementing a fast evolution step, collect and summarize:

1. `~/.hermes/data/EVOLUTION_MANIFEST.json`
   - schema/version/last_updated
   - component and capability counts
   - latest milestones/audits
   - 5D scores and explicit boundaries
2. Rust-native evolution architecture
   - `~/.hermes/apex-evolution-engine`
   - `apex13 --help`
   - src module inventory (`audit.rs`, `background.rs`, `eval.rs`, `evol.rs`, `scout.rs`, etc.)
   - cargo version / metadata where useful
3. Runtime/self-evolution jobs
   - `launchctl list ai.hermes.evol-watcher`
   - `ps` for `apex13 fused-watch`
   - watcher args, watched paths, intervals, logs
4. Python/PGG surfaces
   - benchmark loop
   - provider benchmark
   - provider health gate
   - Delta-G / ECC / provenance / schema / legal gates / case orchestrator
5. Git chain
   - current HEAD
   - recent commits
   - status must be clean before new work unless the dirty state is explicitly in scope

Report the state as a compact panel before saying a chosen implementation is “highest ROI”.

## Implemented class-level pattern

The session evolved the benchmark loop in two safe layers:

### Layer 1 — Replayable failed-example queue

Upgrade failed benchmark records from count-only/simple JSONL to replayable queue items:

- `schema`: `PGGArchonEvolutionQueueItem/v2`
- include `created_at`, `run_id`, `task_id`, `domain`, `prompt`, `scorer`, `weight`, `tags`, `score`, `score_delta`, `priority`, `input_hash`, `attempt_type`, `failure_reason`, `expected`, `prediction`, `next_action`, `promotion_gate`, `boundary`
- add read-only `load_evolution_queue(path, limit=None)` to sort by priority and score delta

### Layer 2 — Read-only proposal worker

Convert prioritized queue items into repair proposals without mutating the system:

- `PGGArchonEvolutionProposal/v1`
- deterministic `proposal_id` from source hash/task/focus
- `repair_focus`
- `proposed_actions`
- `verification_plan`
- `promotion_gate`
- `boundary`

Expose both API and CLI:

```bash
python -m agent.pgg_archon_evolution_proposal \
  --queue <queue.jsonl> \
  --output-dir <dir> \
  --limit 1
```

## Verification pattern

A complete landing requires:

- targeted tests for producer, consumer, proposal generation, and CLI
- `py_compile` for touched modules
- smoke generation from a real queue file
- JSON/JSONL readback and SHA256
- `git diff --check`
- scoped commit of only touched repo files
- `EVOLUTION_MANIFEST.json` update + readback
- explicit boundary: proposal-only, no auto patch, no GeneDB promotion, no scheduler/security/provider mutation

## Pitfalls

- Do not treat queue count as a closed evolution loop; queue items must be replayable and consumable.
- Do not stop at an importable module; add CLI or another runnable entry if a background worker/cron may need it later.
- Do not claim GPT/Claude/DeepSeek/MiniMax participated unless each call produced real evidence; HTTP 200 with empty output is a provider event, not a visible model recommendation.
- Do not import external GitHub code for this pattern; absorb process patterns read-only unless separately authorized and audited.
