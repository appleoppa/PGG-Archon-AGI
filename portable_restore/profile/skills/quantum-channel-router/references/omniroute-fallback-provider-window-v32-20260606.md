# OmniRoute fallback-provider substitution window v3.2 — 2026-06-06

## Status

`PASS_FALLBACK_WINDOW_CROSS_CLASS_ONLY`

## Purpose

Batch-test exact/general substitution canary with primary `gpt55` and fallback `deepseek`. This is fallback provider participation, not GPT same-class substitution.

## API result

```json
{
  "api_ok": true,
  "status": "PASS",
  "sample_count": 20,
  "primary_success_count": 0,
  "fallback_success_count": 20,
  "total_success_count": 20,
  "primary_http_502_count": 20,
  "cross_class_fallback_count": 20,
  "leakage_count": 0
}
```

## Meaning

- gpt55 primary failed on all 20 samples with HTTP 502.
- DeepSeek fallback participated on all 20 samples.
- `cross_class_fallback=true` on all 20 samples.
- legal/audit/AGI leakage remained zero.

## WebUI note

The previous static `omniroute.html` path was not present during v3.2 (`search_files omniroute.html` returned 0). API/snapshot evidence is live; WebUI static button was not patched in this step and must be re-created or re-located in a follow-up WebUI restore step.

## Boundary

This does not prove GPT substitution. It proves a healthy fallback provider lane for low-risk exact/general prompts. Global route-enforce remains disabled.

## Next route

v3.3 should either:

1. restore/recreate the WebUI static page and display v3.2 fallback window; or
2. repair gpt55 502 before attempting same-class substitution again.
