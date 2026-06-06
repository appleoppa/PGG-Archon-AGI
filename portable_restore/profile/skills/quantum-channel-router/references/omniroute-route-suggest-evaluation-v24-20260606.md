# OmniRoute route-suggest evaluation v2.4 — 2026-06-06

## Purpose

Solve the blocker identified by Claude: do not enter route-enforce while suggested provider systematically mismatches actual provider. v2.4 quantifies the mismatch.

## Implemented

- `suggestion_latency_ms` recorded around `decide_omniroute_provider()`.
- `suggestion_error` recorded fail-open.
- `omniroute_route_suggest_metrics(limit=200)` aggregates mirror events.
- Snapshot exposes `route_suggest_metrics`.
- WebUI adds Route-suggest evaluation dashboard.
- Metrics backfill old mirror events by normalizing provider/model into route classes.

## Current verified metrics

```text
suggested_events = 143
suggested_route_class_counts = {mimo: 143}
actual_route_class_counts = {gpt: 99, deepseek: 37, mimo: 4, claude: 3}
mismatch_route_class_pairs = {mimo->gpt: 99, mimo->deepseek: 37, mimo->claude: 3}
class_match_rate = 0.0
suggestion_error_rate = 0.0
avg_suggestion_latency_ms = 1.582
route_enforce_readiness = HOLD
```

## Decision

Route-enforce remains HOLD. The router currently suggests `mimo` for everything while actual traffic is mostly GPT/DeepSeek. This is useful evidence, not a failure of the mirror layer.

## Enforce gates

Do not enter route-enforce until:

1. class_match_rate >= 0.95 over rolling window, or per-task mismatch policy is explicitly approved;
2. suggestion_error_rate <= 0.01;
3. p95 suggestion latency is below threshold;
4. no dominant unknown provider class;
5. enforce feature flag is default-off;
6. canary limited to low-risk prompt classes;
7. rollback/disable path is tested.
