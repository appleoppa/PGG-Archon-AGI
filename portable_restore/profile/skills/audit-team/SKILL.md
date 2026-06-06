---
name: dept-audit-team
version: "1.0.0"
description: 苹果审计组：任务审查与系统监察
metadata:
  {
    "openclaw": {
      "original_id": "shen-ji",
      "original_name": "苹果审计组",
      "timeout": 300,
      "mode": "并行",
      "capabilities": ["任务审计", "质量审查", "系统监察"],
      "model": "DeepSeek-V4-Flash"
    },
    "category": "openclaw-dept",
    "tags": ["审计", "质量", "审查", "监察"]
  }
---

# Audit Team — Compact

## Trigger

Use for task/process audit, completion verification, system governance, legal deliverable quality review, and hallucination/error detection.

## Audit workflow

1. Identify claimed completion and required evidence.
2. Check files, tests, logs, DB rows, legal citations or delivery artifacts.
3. Compare claim vs evidence.
4. Mark PASS/WATCH/BLOCKED.
5. Require correction or internal report when external delivery is unsafe.

## Red flags

Start called completion, missing source, fabricated provider/model participation, unverified legal citation, mixed unrelated files, no rollback path.

## Reference

Full audit matrix archived at `references/full-skill-archive-20260601.md`.
