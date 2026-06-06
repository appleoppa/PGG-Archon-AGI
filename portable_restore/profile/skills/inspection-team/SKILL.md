---
name: dept-inspection-team
version: "1.0.0"
description: 苹果巡视组：独立效验案件执行过程
metadata:
  {
    "openclaw": {
      "original_id": "xun-shi",
      "original_name": "苹果巡视组",
      "timeout": 300,
      "mode": "并行",
      "capabilities": ["独立效验", "过程巡视", "质量检查"],
      "model": "MiniMax-M2.7-highspeed"
    },
    "category": "openclaw-dept",
    "tags": ["巡视", "效验", "质量", "独立"]
  }
---

# Inspection Department — Compact

## Trigger

Use for independent review of case execution process, legal document release gate, evidence/citation consistency, and department handoff quality.

## Workflow

1. Read task goal and claimed output.
2. Verify legal basis, facts, evidence and procedure.
3. Check whether department workflow was actually followed.
4. Mark PASS/WATCH/BLOCKED and list fixes.

## Reference

Full inspection checklist archived at `references/full-skill-archive-20260601.md`.
