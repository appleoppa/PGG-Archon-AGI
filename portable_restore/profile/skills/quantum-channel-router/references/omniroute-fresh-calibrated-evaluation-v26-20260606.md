# OmniRoute fresh calibrated evaluation v2.6 — 2026-06-06

## Purpose

Separate pre-calibration rolling metrics from fresh route-policy metrics. v2.6 adds `route_policy_version` to route decisions and mirror events, then exposes `post_policy_window` in route-suggest metrics.

## Code changes

- `OMNIROUTE_ROUTE_POLICY_VERSION = v2.6-fresh-calibrated-window-20260606`
- `decide_omniroute_provider()` now writes `route_policy_version`.
- `record_omniroute_core_mirror()` persists `route_policy_version`.
- `omniroute_route_suggest_metrics(limit, policy_version=...)` filters fresh windows.
- API snapshot includes `route_suggest_metrics.post_policy_window`.
- WebUI displays rolling metrics and post-policy metrics separately.

## Classifier correction

v2.5 exposed a priority bug: prompts containing both `PGG` and `audit/judge` matched AGI before audit. v2.6 order is:

```text
legal -> audit/judge -> exact/math -> AGI/coding/evolution -> general
```

## Real fresh-window smoke

Five real core conversations were executed with actual provider `custom:gpt55_5yuantoken`:

```text
legal   suggested=deepseek actual=gpt class_match=false answer=PGG_V26B_LEGAL_OK
agi     suggested=gpt55   actual=gpt class_match=true  answer=PGG_V26B_AGI_OK
audit   suggested=mimo    actual=gpt class_match=false answer=PGG_V26B_AUDIT_OK
exact   suggested=gpt55   actual=gpt class_match=true  answer=PGG_V26B_EXACT_OK
general suggested=gpt55   actual=gpt class_match=true  answer=PGG_V26B_GENERAL_OK
```

## Verified metrics

```json
{
  "policy_version_filter": "v2.6-fresh-calibrated-window-20260606",
  "suggested_events": 5,
  "class_match_count": 3,
  "class_match_rate": 0.6,
  "suggestion_error_rate": 0.0,
  "avg_suggestion_latency_ms": 0.76,
  "max_suggestion_latency_ms": 1.542,
  "suggested_route_class_counts": {"gpt": 3, "deepseek": 1, "mimo": 1},
  "actual_route_class_counts": {"gpt": 5},
  "mismatch_route_class_pairs": {"deepseek->gpt": 1, "mimo->gpt": 1},
  "route_enforce_readiness": "HOLD"
}
```

## Decision

Route-suggest policy is now observable and no longer polluted by old all-MiMo events. However route-enforce remains **HOLD** because actual Desktop/Core traffic still stays on the user-selected GPT provider, while policy suggests DeepSeek for legal and MiMo for audit. Enforcing those suggestions would mutate the provider path and needs a separate guarded canary with explicit feature flag and rollback.

## Boundary

This is route-suggest observability, not route-enforce approval, not benchmark, and not legal correctness proof.
