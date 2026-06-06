# PilotDeck self-evolution pipeline + evidence-chain gate (2026-06-03)

## Trigger

Use when guiding PilotDeck as an independent agent through self-repair, self-evolution, model governance, or any claim that a PilotDeck evolution round is `DONE`.

## Durable pattern

PilotDeck evolution should not be reported from natural-language summaries alone. It must run a deterministic pipeline, write machine-readable evidence, and then ask PilotDeck itself to read back/absorb the result.

### Required 8-step execution order

1. **File scan** — scan PilotDeck hidden deployment/repo/report paths; count files, bytes, extensions, and suspicious samples.
2. **Karpathy check** — simple, source-grounded sanity scan for fake success / low-signal patterns: `mock`, `simulated`, `dry_run`, `time.sleep`, hardcoded `status: done`, and duplicate-line diagnostics.
3. **Import parse** — parse Python with AST and run the TypeScript/Node build path (`npm run build`) as the real import/build proxy.
4. **Integrated report** — read config/model boundary facts: providers, agent model, memory model, fallback, config SHA.
5. **EVM monitor** — compute a runtime score from service ports, main-model boundary, fallback boundary, build pass, and Karpathy pass. PASS threshold: `>=75`.
6. **Tao correction** — if EVM or Karpathy fails, do not mutate blindly; emit corrective action and stop/mark WATCH. If clean, continue evidence-only hardening.
7. **β_bg evolution** — compute a bounded confidence score; PASS threshold: `>=0.75`; emit next actions.
8. **Pipeline completion** — only PASS if the previous seven gates PASS.

## Current local implementation

- Pipeline script: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evolution_pipeline_round7.py`
- Evidence-chain wrapper: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evidence_chain_round8.py`
- Evidence log: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evidence_chain.jsonl`

These paths are in PilotDeck's hidden home. Do not copy them to Home root or Hermes workspace unless the user explicitly requests an external artifact.

## Completion gate

From Round 8 onward:

> No `pilotdeck_evidence_chain.jsonl` record means no `DONE` claim for PilotDeck self-evolution.

A valid evidence-chain record uses schema `PilotDeckEvidenceChain/v1` and must include:

- `input` — user goal and scripts used
- `hashes` — at least `pilotdeck.yaml`, pipeline script, invariant script, pipeline JSON
- `runtime_evidence` — ports, invariant result, pipeline result, npm build exit, EVM, β_bg, 8-step statuses
- `rollback_point` — explicit files/log entries to remove if the additive round must be reverted
- `final_verdict` — derived from runtime evidence, not manually asserted
- `model_boundary` — MIMO main/tools; GPT advisory-only/no-tools via authenticated bridge; Agnes chat-only/no-tools

Recommended PASS logic:

```text
final_verdict = PASS iff invariants_ok && pipeline_ok && all required ports ready
```

## Model boundary that must not drift

- **MIMO**: main controller; tools/router/fallback/memory/tokenSaver.
- **GPT-5.5**: advisory-only/no-tools through authenticated local bridge.
- **Agnes**: chat-only/no-tools.

Do not add GPT or Agnes to execution fallback/tool routes while applying this pattern.

## Verification checklist

Before reporting completion:

```bash
python3 /Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/verify_pilotdeck_invariants.py
python3 /Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evidence_chain_round8.py
```

Then read back the latest JSONL line and verify:

```text
schema = PilotDeckEvidenceChain/v1
final_verdict = PASS
runtime_evidence.evm_score >= 75
runtime_evidence.beta_bg >= 0.75
runtime_evidence.step_status.* = PASS
```

## Pitfalls

- Do not treat a PilotDeck chat response saying `DONE` as enough. Read the report and the JSONL record.
- Do not let `npm run build` failure be hidden by a natural-language report.
- Do not count `/health` reachability alone as GPT bridge capability. Protected endpoints (`/v1/models`, `/v1/chat/completions`) must verify bearer auth when bridge auth is in scope.
- Re-running the evidence wrapper appends a new JSONL line. This is expected; report the final line count and latest verdict.
