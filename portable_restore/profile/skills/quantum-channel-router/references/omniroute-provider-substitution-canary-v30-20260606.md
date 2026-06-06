# OmniRoute provider substitution canary v3.0 — 2026-06-06

## Status

`PARTIAL_SCAFFOLD_PLAN_PASS_EXECUTION_BLOCKED_BY_GPT55_502`

## Implemented

- Substitution event ledger: `~/.hermes/data/omniroute_provider_substitution_events.jsonl`
- `plan_provider_substitution_canary()`
- `execute_provider_substitution_canary()`
- API: `POST /api/omniroute/substitution/plan`
- API: `POST /api/omniroute/substitution/canary`
- WebUI buttons: `Plan substitution`, `Run substitution canary`
- Snapshot exposes latest substitution canary and recent substitution events.

## Plan result

```json
{
  "plan_ok": true,
  "allowed": true,
  "provider": "gpt55"
}
```

## Execution result

```json
{
  "api_ok": false,
  "success": false,
  "executed": true,
  "registry_http": 502,
  "registry_participated": false,
  "registry_error": "http_status=502",
  "fallback_http": 0,
  "fallback_participated": false,
  "fallback_error": "core fallback returned API failure text"
}
```

## Truthfulness correction

A first core fallback attempt returned visible failure text (`API call failed after 3 retries: HTTP 502...`). v3.0 was patched so failure text is not counted as provider participation. Final canary correctly reports failure.

## Current blocker

The exact/general substitution plan is allowed by guards, but real execution is blocked because gpt55 provider calls return HTTP 502 both through the external benchmark registry and Hermes Core fallback. Therefore v3.0 cannot be marked as successful provider substitution.

## Boundary

No global route-enforce was enabled. Legal/audit/AGI remain denied. This is not benchmark or AGI proof.

## Next step

Fix or swap the callable provider execution lane before any wider substitution:

1. diagnose ChuangAgent gpt55 502 from both registry and Core;
2. if unavailable, use a healthy exact/general provider lane for canary (e.g. DeepSeek if policy permits same-class gate is changed explicitly);
3. rerun single-provider participation proof;
4. only then rerun v3.0 substitution canary.
