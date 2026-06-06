# AGI task benchmark harness pattern

Use when the user asks to push PGG Archon/Hermes toward AGI quickly, efficiently, and truthfully.

## Core lesson

The fastest high-ROI AGI evolution step is not more grand naming, overlay expansion, or internal self-scores. The durable move is to establish a repeatable task loop:

```text
task -> prediction -> deterministic scoring -> failed examples -> evolution queue -> verified patch
```

This turns evolution from report-driven self-assessment into task-failure-driven improvement.

## Minimal harness shape

A bounded first implementation should include:

- `BenchmarkTask`: task_id, domain, prompt, expected, scorer, weight, tags.
- Deterministic scorers:
  - normalized exact match
  - normalized contains
  - JSON object equality
- `evaluate_predictions(tasks, predictions)`: returns total tasks, passed tasks, weighted score, status, failed task IDs.
- Output artifacts:
  - run JSON
  - per-task scores JSONL
  - failed-task `evolution_queue.jsonl`
- Failed queue item fields:
  - run_id
  - task_id
  - domain
  - failure_reason
  - expected
  - prediction
  - next_action, e.g. `analyze_failure_and_add_capability_or_prompt_fix`
  - boundary statement

## Verification gate

Before claiming completion:

1. Run deterministic unit tests for every scorer and output file.
2. Execute both a WATCH sample and a PERFECT/PASS sample.
3. Confirm WATCH sample writes at least one failed queue item.
4. Confirm PERFECT sample writes an empty queue.
5. Run an existing core regression subset.
6. Call GPT + Claude + DeepSeek with evidence if the work is framed as AGI evolution.
7. Commit only the harness and tests.
8. Update `EVOLUTION_MANIFEST.json` and the current evolution ledger; read both back.

## Boundary wording

Always state:

- This is an internal deterministic benchmark harness.
- It is not an external AGI benchmark result.
- It is not full AGI proof.
- It is not legal correctness proof.

## Fast-path sprint sequence

Sprint 1:
- Build the internal deterministic task harness.
- Generate sample WATCH/PASS runs.
- Ensure failed tasks enter the evolution queue.

Sprint 2:
- Connect real provider/model predictions from GPT/Claude/DeepSeek to the same tasks.
- Compare per-model scores.
- Feed failures into the queue.

Sprint 3:
- Implement verified fixes against queued failures.
- Re-run the same tasks to measure improvement.
- Only then write GeneDB/manifest/evolution claims.

## Pitfalls

- Do not call the harness an AGI benchmark.
- Do not treat APEX ΔE or internal score as external capability proof.
- Do not auto-fix queued failures without a tested patch.
- Do not skip model audit when the user explicitly authorizes all LLM/GitHub resources for AGI evolution.
