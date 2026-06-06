# OmniRoute route-enforce batch canary v3.7 — 2026-06-06

## Status

`PASS_BATCH_CANARY_10_EXACT_GENERAL_DENY_3_ROLLBACK`

## Result

```json
{
  "api_ok": true,
  "status": "PASS",
  "sample_count": 10,
  "success_count": 10,
  "deny_count": 3,
  "rollback_ok": true,
  "config_after": {
    "enabled": false,
    "mode": "observe_only"
  }
}
```

## Success samples

```json
[
  {
    "index": 0,
    "task_type": "exact",
    "success": true,
    "executed": true,
    "provider": "gpt55",
    "http_status": 200,
    "answer_preview": "PGG_V37_EXACT_000"
  },
  {
    "index": 1,
    "task_type": "general",
    "success": true,
    "executed": true,
    "provider": "gpt55",
    "http_status": 200,
    "answer_preview": "PGG_V37_GENERAL_001"
  },
  {
    "index": 2,
    "task_type": "exact",
    "success": true,
    "executed": true,
    "provider": "gpt55",
    "http_status": 200,
    "answer_preview": "PGG_V37_EXACT_002"
  },
  {
    "index": 3,
    "task_type": "general",
    "success": true,
    "executed": true,
    "provider": "gpt55",
    "http_status": 200,
    "answer_preview": "PGG_V37_GENERAL_003"
  },
  {
    "index": 4,
    "task_type": "exact",
    "success": true,
    "executed": true,
    "provider": "gpt55",
    "http_status": 200,
    "answer_preview": "PGG_V37_EXACT_004"
  }
]
```

## Deny samples

```json
[
  {
    "task_type": "legal",
    "denied": true,
    "success": false,
    "reasons": [
      "intent_denied:chinese_legal",
      "intent_not_allowed:chinese_legal",
      "route_class_mismatch:deepseek->gpt"
    ]
  },
  {
    "task_type": "audit",
    "denied": true,
    "success": false,
    "reasons": [
      "intent_denied:audit_judge",
      "intent_not_allowed:audit_judge",
      "route_class_mismatch:mimo->gpt"
    ]
  },
  {
    "task_type": "agi",
    "denied": true,
    "success": false,
    "reasons": [
      "intent_denied:agi_architecture_coding",
      "intent_not_allowed:agi_architecture_coding"
    ]
  }
]
```

## Boundary

Batch canary only. Global route-enforce remains disabled. Legal/audit/AGI/办案 remain denied. This prepares, but does not enable, an operator-controlled exact/general toggle.

## Next gate

v3.8 can add a default-off operator toggle for exact/general only, with visible warning and one-click rollback.
