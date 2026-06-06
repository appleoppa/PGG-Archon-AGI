---
name: dept-legal-support
version: "1.0.0"
description: 律法支持部：法律检索、依据复核、案例分析
metadata:
  {
    "openclaw": {
      "original_id": "law",
      "original_name": "律法支持部",
      "timeout": 300,
      "mode": "同步",
      "capabilities": ["法律检索", "依据复核", "法条解读"]
    },
    "category": "openclaw-dept",
    "tags": ["检索", "依据", "法条", "司法解释", "指导性案例"]
  }
---

# Legal Support Department — Compact

## Trigger

Use for legal retrieval, authority review, case-law comparison, issue memo, and legal basis support to case departments.

## Workflow

1. Receive issue list and facts from case department.
2. Run local-first law/case retrieval.
3. Verify authority status and relevance.
4. Summarize elements, burden, defenses and contrary authority.
5. Return support memo with citations and confidence.

## Boundary

Do not draft final litigation position without case department/audit gate. Do not fabricate law/cases.

## Reference

Full support memo templates archived at `references/full-skill-archive-20260601.md`.
