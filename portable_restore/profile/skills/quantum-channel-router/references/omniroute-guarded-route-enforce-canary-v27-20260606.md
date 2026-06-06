# OmniRoute guarded route-enforce canary v2.7 — 2026-06-06

## Status

`PASS_SCAFFOLD_DEFAULT_OFF`

## Claude participation

A real Claude Responses API call was attempted through ChuangAgent `/v1/responses`:

```json
{
  "provider": "claude_opus46_5yuantoken",
  "http_status": 0,
  "ok": false,
  "visible_chars": 0,
  "error": "<HTTPError 403: 'Forbidden'>"
}
```

Evidence file: `/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/claude-v27-route-enforce-canary-review-20260606.json`

Claude did not successfully participate in this v2.7 run. The implementation follows the prior Claude HOLD principle already recorded in v2.4/v2.5: route-enforce must stay default-off until mismatch metrics and guardrails are ready.

## Implemented

- `OMNIROUTE_ENFORCE_CONFIG`: `~/.hermes/data/omniroute_route_enforce_canary.json`
- `OMNIROUTE_ENFORCE_EVENTS`: `~/.hermes/data/omniroute_route_enforce_events.jsonl`
- `read_route_enforce_canary_config()` / `write_route_enforce_canary_config()`
- `evaluate_route_enforce_canary()`
- Mirror payload now records `route_enforce_canary` and `route_enforce_would_enforce`.
- API snapshot includes `route_enforce_canary` config and recent events.
- API endpoint: `POST /api/omniroute/enforce/config`
- WebUI route-suggest panel displays canary status.

## Default config

```json
{
  "enabled": false,
  "mode": "observe_only",
  "allowed_intents": ["bounded_exact_or_math", "general"],
  "denied_intents": ["chinese_legal", "audit_judge", "agi_architecture_coding"],
  "require_route_class_match_actual": true,
  "require_policy_version": "v2.6-fresh-calibrated-window-20260606"
}
```

## Real verification

Offline guard smoke:

```text
exact default-off -> allowed=false reasons=[config_disabled_default_off]
legal default-off -> denied + mismatch deepseek->gpt
audit default-off -> denied + mismatch mimo->gpt
canary exact with enabled=true -> allowed=true
rollback -> enabled=false mode=observe_only
```

Real core smoke:

```text
PGG_V27_EXACT_DEFAULT_OFF_OK  suggested=gpt55 actual=gpt would_enforce=false
PGG_V27_LEGAL_DEFAULT_OFF_OK  suggested=deepseek actual=gpt would_enforce=false denied legal + mismatch
```

API verification:

```text
py_compile OK
snapshot route_enforce_canary OK
POST /api/omniroute/enforce/config OK
WebUI contains route_enforce_canary OK
```

## Decision

This is a guarded scaffold only. It does not mutate provider routing. Formal route-enforce remains HOLD because v2.6 fresh class_match_rate is 0.6 and legal/audit mismatch the current GPT path.
