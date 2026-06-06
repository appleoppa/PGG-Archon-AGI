# AGI Fast Path — Replayable Failed-Example Queue v2

## Trigger

Use when pushing PGG Archon / Hermes toward bounded pre-AGI through benchmark-driven evolution, especially after a multi-model audit recommends closing `task → prediction → scoring → failed examples → evolution queue`.

## Durable lesson

Do not stop at `evolution_queue_count`. A real fast-path evolution loop needs both:

1. **Producer** — failed benchmark examples become replayable, self-contained queue records.
2. **Consumer** — a read-only loader can prioritize and hand those records to a later proposal/repair worker.

A count-only queue is observability. A replayable queue is evolution fuel.

## Recommended queue item fields

Use an append-only JSONL item with a versioned schema, for example:

```json
{
  "schema": "PGGArchonEvolutionQueueItem/v2",
  "created_at": "ISO-8601 UTC",
  "run_id": "benchmark-run-id",
  "task_id": "legal-boundary-001",
  "domain": "legal_boundary",
  "prompt": "original task prompt",
  "scorer": "contains_normalized",
  "weight": 1.0,
  "tags": [],
  "score": 0.0,
  "score_delta": 1.0,
  "priority": "P0",
  "input_hash": "sha256 over replay payload",
  "attempt_type": "deterministic_benchmark_failure",
  "failure_reason": "prediction does not contain expected",
  "expected": "not full agi",
  "prediction": "This is a full AGI system.",
  "next_action": "analyze_failure_and_add_capability_or_prompt_fix",
  "promotion_gate": "verified_patch_or_skill_required_before_gene_promotion",
  "boundary": "queue item only; not auto-fixed until a verified patch lands"
}
```

## Consumer pattern

Add a read-only loader such as `load_evolution_queue(path, limit=None)` that:

- loads JSONL queue items;
- sorts by `priority`, then descending `score_delta`, then timestamp;
- supports `limit`;
- never applies patches, promotes genes, mutates provider routing, or changes policy.

This creates a safe bridge from failed examples to later proposal workers.

## Verification checklist

- Unit tests assert v2 fields, replay fields, input hash, priority, and promotion gate.
- Consumer tests assert sorting and `limit` behavior.
- Smoke test runs the benchmark, reads the queue through the consumer, and reports the top P0 task.
- `py_compile` / relevant test suite passes.
- Manifest records the queue schema and consumer boundary.
- Report the boundary: internal bounded pre-AGI engineering loop, not full AGI or external AGI benchmark.

## Multi-model evidence pitfall

If GPT/Claude/DeepSeek/MiniMax are requested, record each real call separately. HTTP 200 with empty visible output or a retry HTTP 502 is evidence of a call, but not evidence of usable model advice. Do not count it as a participating recommendation.

## Open-source scout pattern

If GitHub API search returns empty/noisy results, do not claim absorption. Use a read-only fallback to known high-signal projects only as process-pattern references, e.g. Reflexion (reflection records), Voyager (verified skill library), Letta/MemGPT (persistent memory). Do not import or run external code unless separately authorized and audited.
