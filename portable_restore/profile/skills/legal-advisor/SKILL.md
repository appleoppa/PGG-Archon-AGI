---
name: dept-legal-advisor
version: "1.0.0"
description: 法律顾问部：合同审查、法律意见、公司治理
metadata:
  {
    "openclaw": {
      "original_id": "gu-wen",
      "original_name": "法律顾问部",
      "timeout": 240,
      "mode": "异步/同步",
      "jurisdiction": ["合同审查", "法律意见", "公司治理", "股权", "章程"]
    },
    "category": "openclaw-dept",
    "tags": ["顾问", "合同", "法律意见", "公司治理", "股权"]
  }
---

# Legal Advisor Department — Compact

## Trigger

Use for routine legal counsel, contract review, company governance, compliance, legal opinion, demand letters and risk consultation.

## Workflow

1. Identify business goal, parties, document/facts and jurisdiction.
2. Spot key legal issues and missing facts.
3. Research authority when legal conclusion is needed.
4. Provide options, risk level, recommended action and document changes.
5. Mark items requiring user/lawyer confirmation.

## Output

`issue`, `risk`, `basis`, `recommendation`, `documents_needed`, `boundary`.

## Reference

Full advisory workflow archived at `references/full-skill-archive-20260601.md`.
