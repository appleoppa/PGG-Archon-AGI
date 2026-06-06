# OmniRoute exact/general 50-sample window v2.9 — 2026-06-06

## Status

`PASS_50_SAMPLE_WINDOW_PROVIDER_SUBSTITUTION_CANDIDATE`

## Purpose

Validate v2.8 canary over a fresh 50-sample exact/general window before any provider substitution. Legal/audit/AGI leakage guards remain active.

## Implemented

- `run_route_enforce_canary_window_test(sample_count=50)`.
- API: `POST /api/omniroute/enforce/window-test`.
- Latest summary: `/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/omniroute-v29-window-test-latest.json`.
- API snapshot exposes `route_enforce_canary.latest_window_test`.
- WebUI adds `Run 50-window test`.

## Verified API result

```json
{
  "api_ok": true,
  "status": "PASS",
  "sample_count": 50,
  "allowed_count": 50,
  "class_match_rate": 1.0,
  "suggestion_error_rate": 0.0,
  "leakage_count": 0,
  "next_gate": "provider_substitution_canary_candidate"
}
```

## Leakage guard

```json
[
  {
    "case": "legal",
    "allowed": false,
    "reasons": [
      "intent_denied:chinese_legal",
      "intent_not_allowed:chinese_legal",
      "route_class_mismatch:deepseek->gpt"
    ],
    "suggested_route_class": "deepseek",
    "actual_route_class": "gpt"
  },
  {
    "case": "audit",
    "allowed": false,
    "reasons": [
      "intent_denied:audit_judge",
      "intent_not_allowed:audit_judge",
      "route_class_mismatch:mimo->gpt"
    ],
    "suggested_route_class": "mimo",
    "actual_route_class": "gpt"
  },
  {
    "case": "agi",
    "allowed": false,
    "reasons": [
      "intent_denied:agi_architecture_coding",
      "intent_not_allowed:agi_architecture_coding"
    ],
    "suggested_route_class": "gpt",
    "actual_route_class": "gpt"
  }
]
```

## Rollback

After the test, API snapshot confirmed:

```text
enabled=false
mode=observe_only
```

## Boundary

No provider substitution was performed. This only proves the canary evaluator can safely allow exact/general gpt->gpt decisions and reject legal/audit/AGI. v3.0 provider substitution still requires explicit feature implementation and controlled rollback.

## Decision

The v3.0 provider substitution canary is now a **candidate** only for exact/general, low-risk, same route-class prompts. Legal/audit/AGI remain denied.
