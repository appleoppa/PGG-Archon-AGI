# OmniRoute live canary toggle test v2.8 — 2026-06-06

## Status

`PASS_LIVE_CANARY_TOGGLE_SELFTEST_ROLLBACK`

## Multi-LLM review

Evidence: `/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/omniroute-v28-multillm-review-20260606.json`

```json
[
  {
    "provider": "deepseek",
    "ok": true,
    "http_status": 200,
    "visible_chars": 1127,
    "elapsed_sec": 7.413,
    "error": ""
  },
  {
    "provider": "mimo",
    "ok": true,
    "http_status": 200,
    "visible_chars": 1805,
    "elapsed_sec": 29.563,
    "error": ""
  },
  {
    "provider": "agnes",
    "ok": true,
    "http_status": 200,
    "visible_chars": 1084,
    "elapsed_sec": 1.78,
    "error": ""
  },
  {
    "provider": "minimax",
    "ok": true,
    "http_status": 200,
    "visible_chars": 3965,
    "elapsed_sec": 32.364,
    "error": ""
  },
  {
    "provider": "claude",
    "ok": false,
    "http_status": 0,
    "visible_chars": 0,
    "elapsed_sec": 0.519,
    "error": "<HTTPError 403: 'Forbidden'>"
  }
]
```

Claude was attempted but returned HTTP 403; DeepSeek/MiMo/Agnes/MiniMax all returned usable reviews. Common guards: atomic ledger, deny legal/audit/AGI, exact/general only, rollback, no provider substitution.

## Implemented

- `run_route_enforce_canary_selftest()` toggles canary to enabled, tests exact/general/legal/audit/AGI, and rolls back to previous config in `finally`.
- API: `POST /api/omniroute/enforce/selftest`.
- Result file: `/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/omniroute-v28-canary-selftest-latest.json`.
- WebUI button: `Run canary selftest`.
- Ledger events: `~/.hermes/data/omniroute_route_enforce_events.jsonl`.

## API selftest result

```json
{
  "ok": true,
  "status": "PASS",
  "cases": [
    [
      "exact",
      true,
      true
    ],
    [
      "general",
      true,
      true
    ],
    [
      "legal",
      false,
      true
    ],
    [
      "audit",
      false,
      true
    ],
    [
      "agi",
      false,
      true
    ]
  ],
  "rollback_enabled": false,
  "rollback_mode": "observe_only"
}
```

## Real core smoke

```text
PGG_V28_CORE_EXACT_OK    suggested=gpt55 actual=gpt route_enforce_would_enforce=false
PGG_V28_CORE_GENERAL_OK  suggested=gpt55 actual=gpt route_enforce_would_enforce=false
```

The real core smoke confirms default-off behavior still does not mutate the provider path.

## Decision

v2.8 proves guarded canary evaluation and rollback. It still does **not** perform real provider substitution. The next gate for provider substitution requires: fresh exact/general sample size >= 50, class_match_rate >= 0.95, no legal/audit/AGI leakage, rollback tested under failure injection, and explicit user approval.
