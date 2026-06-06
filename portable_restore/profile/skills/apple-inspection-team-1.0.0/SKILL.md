---
name: apple-inspection-team
version: "1.0.0"
description: 苹果巡视组：效验法条依据与文书准确性
author: 苹果哥
category: legal
tags: [inspection, legal, review, quality, workflow, automation]
language: zh
metadata:
  {
    "openclaw": {
      "requires": { "env": [] },
      "capabilities": ["reasoning", "file_read"],
      "evolution": {
        "enabled": true,
        "version": "1.0.0"
      }
    }
  }
---

# Apple Inspection Team — Compact

## Trigger

Use to independently verify legal basis, document accuracy, citations, case facts, calculation, evidence references, and whether a legal deliverable may be released.

## Inspection gates

1. Fact consistency: names, dates, amounts, contracts, procedural stage.
2. Law/case verification: no fabricated article/case/source.
3. Evidence matching: every key assertion has support or is marked unsupported.
4. Procedure: jurisdiction, limitation, burden, applications, deadlines.
5. Output readiness: external version vs internal report.

## Result labels

- `PASS`: deliverable can proceed.
- `WATCH`: usable but needs confirmation/supplement.
- `BLOCKED`: cannot release due to missing/false basis or evidence gap.

## Reference

Full checklist archived at `references/full-skill-archive-20260601.md`.
