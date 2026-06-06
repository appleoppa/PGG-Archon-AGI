---
name: apple-legal-polish
version: "1.0.0"
description: 法律文书润色：12种润色维度
author: 苹果哥
category: legal
tags: [legal, writing, polish, document, lawyer, china]
language: zh
parent: apple-lawyer-suite
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

# Apple Legal Polish — Compact

## Trigger

Use to polish legal documents without changing unsupported facts or legal meaning: pleadings, opinions, memos, contracts, letters, applications, trial outlines.

## Polish dimensions

- legal accuracy;
- issue structure;
- fact chronology;
- claim/legal-element matching;
- evidence citation;
- tone and professionalism;
- concision;
- court/authority readability;
- risk language;
- formatting;
- consistency of names/dates/amounts;
- delivery readiness.

## Hard boundary

Do not invent facts, laws, case numbers, evidence, signatures, dates, or authority citations. If source support is missing, mark it.

## Workflow

1. Determine document purpose and audience.
2. Preserve facts and legal position.
3. Improve structure and wording.
4. Check internal consistency.
5. Mark items needing lawyer/user confirmation.

## Reference

Full 12-dimension examples archived at `references/full-skill-archive-20260601.md`.
