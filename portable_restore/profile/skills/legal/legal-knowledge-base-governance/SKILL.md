---
name: legal-knowledge-base-governance
description: 法律知识库/向量库治理：本地官方指导案例库和法律法规库优先，外部公开源补充，结构化条文/案例字段化/混合检索/评测闭环。
---

# Legal Knowledge Base Governance — Compact

## Trigger

Use for legal KB/vector DB governance, official corpus connection, normalized law/case fields, hybrid retrieval, benchmark, and corpus quality control.

## Rule

Local official law and guiding-case corpus is primary. External public sources are supplement and cross-check only.

## Workflow

1. Inventory local corpus paths, counts, source type and update status.
2. Normalize fields: title, article_no, effective status, source_path, case_no, court, issue, rule.
3. Build hybrid retrieval: exact article/case + keyword/vector.
4. Evaluate with benchmark queries and regression gate.
5. Report coverage, gaps, conflicts and refresh plan.

## Boundary

KB hit is not final legal opinion; external delivery still needs source/effective-status review.

## Reference

Full KB governance archived at `references/full-skill-archive-20260601.md`.
