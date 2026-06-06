# OmniRoute callable provider lane repair v3.1 — 2026-06-06

## Status

`PASS_FALLBACK_PROVIDER_PARTICIPATION_PRIMARY_GPT55_BLOCKED`

## Diagnosis

```json
[
  {
    "lane": "gpt55_direct_responses",
    "ok": false,
    "http_status": 0,
    "visible_chars": 0,
    "text_preview": "",
    "error": "<HTTPError 502: 'Bad Gateway'>",
    "elapsed_sec": 0.751
  },
  {
    "lane": "gpt55_core",
    "ok": false,
    "http_status": 0,
    "visible_chars": 0,
    "text_preview": "",
    "error": "TypeError(\"unsupported operand type(s) for |: 'type' and 'type'\")",
    "elapsed_sec": 0.063
  },
  {
    "lane": "gpt55_registry",
    "ok": false,
    "http_status": 502,
    "visible_chars": 0,
    "text_preview": "",
    "error": "http_status=502",
    "elapsed_sec": 1.016
  },
  {
    "lane": "deepseek_registry",
    "ok": true,
    "http_status": 200,
    "visible_chars": 19,
    "text_preview": "PGG_V31_DEEPSEEK_OK",
    "error": "",
    "elapsed_sec": 1.098
  },
  {
    "lane": "mimo_registry",
    "ok": true,
    "http_status": 200,
    "visible_chars": 15,
    "text_preview": "PGG_V31_MIMO_OK",
    "error": "",
    "elapsed_sec": 8.68
  }
]
```

Findings:

- gpt55 direct `/v1/responses`: HTTP 502
- gpt55 benchmark registry: HTTP 502
- Hermes Core gpt55 diagnostic in this script hit local import/runtime issue; prior Core fallback returned HTTP 502 failure text and is not counted as participation
- DeepSeek registry: OK
- MiMo registry: OK, but reserved for judge/audit paths

## v3.1 change

`execute_provider_substitution_canary()` now supports a healthy fallback provider lane. If primary gpt55 fails, it can execute DeepSeek as fallback provider participation proof, while explicitly marking:

```text
cross_class_fallback = true
same_class_substitution_success = false
fallback_participation_success = true
```

## Verified canary

```json
{
  "api_ok": true,
  "success": true,
  "same_class_success": false,
  "fallback_success": true,
  "primary_provider": "gpt55",
  "primary_http": 502,
  "primary_participated": false,
  "fallback_provider": "deepseek",
  "fallback_http": 200,
  "fallback_participated": true,
  "cross_class_fallback": true,
  "fallback_answer": "PGG_V31_FALLBACK_OK"
}
```

## Boundary

This is **not** GPT same-class substitution success. It is callable lane repair: when gpt55 is unavailable, DeepSeek can execute the exact/general bounded prompt and produce provider participation evidence. Legal/audit/AGI remain denied. Global route-enforce remains disabled.

## Next gate

v3.2 can proceed only as `fallback-provider substitution canary`, not GPT same-class substitution, unless gpt55 recovers.
