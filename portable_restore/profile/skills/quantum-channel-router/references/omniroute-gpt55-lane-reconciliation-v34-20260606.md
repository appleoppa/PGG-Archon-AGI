# OmniRoute GPT55 lane reconciliation v3.4 — 2026-06-06

## Status

`PASS_GPT55_PROOF_LANE_REPAIRED`

## User correction

The user correctly pointed out that the main session has been using GPT55 throughout. The previous wording "gpt55 unavailable" was imprecise. The true issue was:

```text
GPT55 main/orchestrator lane: available and used
GPT55 OmniRoute substitution proof lane: previously broken due to payload mismatch
```

## Root cause

`agent.pgg_archon_external_benchmark_provider_run.call_provider()` used this Responses payload shape:

```json
{"input": [{"role":"system"}, {"role":"user"}], "max_tokens": 4096, "max_output_tokens": 4096}
```

ChuangAgent gpt-5.5 can return HTTP 502 for that shape.

The known-good runtime-compatible shape from `pgg_archon_provider_benchmark` is:

```json
{"model":"gpt-5.5", "input":"...", "max_completion_tokens": 4096}
```

with fallback:

```json
{"model":"gpt-5.5", "input":"...", "max_tokens": 4096}
```

## Fix

Patched:

```text
/Users/appleoppa/.hermes/hermes-agent/agent/pgg_archon_external_benchmark_provider_run.py
```

Now gpt55 registry proof lane uses plain Responses input string + `max_completion_tokens`, retrying with `max_tokens`.

## Verification

Registry smoke:

```text
PGG_V34_REGISTRY_OK
http_status=200
parsed_text=PGG_V34_REGISTRY_OK
```

Substitution canary direct Python:

```json
{
  "success": true,
  "same_class_success": true,
  "fallback_success": false,
  "primary_http": 200,
  "primary_participated": true,
  "primary_answer": "PGG_V34_SUBSTITUTION_OK"
}
```

API canary:

```json
{
  "success": true,
  "same_class_success": true,
  "fallback_success": false,
  "primary_http": 200,
  "primary_participated": true,
  "primary_answer": "PGG_V34_API_SUBSTITUTION_OK"
}
```

## Corrected state

```text
GPT55 main lane: OK
GPT55 proof lane: repaired OK
DeepSeek fallback lane: still available, but no longer needed for exact/general GPT same-class canary when gpt55 is healthy
legal/audit/AGI substitution: still denied
route-enforce global: still disabled
```
