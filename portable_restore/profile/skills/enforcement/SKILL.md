---
name: dept-enforcement
version: "1.0.0"
description: 强制执行部：判决/调解书的强制执行事务
metadata:
  {
    "openclaw": {
      "original_id": "zhi-xing",
      "original_name": "强制执行部",
      "timeout": 240,
      "mode": "异步",
      "jurisdiction": ["财产查控", "执行异议", "追加变更", "执行和解"]
    },
    "category": "openclaw-dept",
    "tags": ["执行", "查控", "异议", "追加变更", "强制执行"]
  }
---

# Enforcement Department — Compact

## Trigger

Use for enforcement of judgments/settlements/arbitral awards, property clues, execution objections, preservation-to-enforcement handoff, and debtor asset strategy.

## Workflow

1. Confirm effective instrument, amount, parties and limitation for enforcement.
2. Collect debtor/property clues and prior preservation status.
3. Prepare enforcement application and evidence.
4. Analyze measures: freeze, auction, consumption restriction, blacklist, objection/reconsideration.
5. Report collectability risk.

## Reference

Full enforcement checklist archived at `references/full-skill-archive-20260601.md`.
