---
name: local-first-legal-kb
description: 本地优先法律知识库检索：调用苹果中枢本地官方指导案例库、法律法规库与条文级检索 CLI，避免外部公开源覆盖本地主库。
version: 1.0.0
created: 2026-06-01
---

# Local First Legal KB — Compact

## Trigger

Use whenever Chinese legal research, statutes, guiding cases, local official corpus, article lookup, or case research pack is needed.

## Rule

Search local official legal KB first. External public sources are supplement only. Never replace local main corpus with external samples.

## Workflow

1. Classify query: law article, document/case, guiding case, research pack.
2. Use local_legal_kb with targeted query/article/case fields.
3. Verify title, article number, effective status, source collection and relevance.
4. Return concise rule/application and mark gaps.

## Reference

Full local KB governance archived at `references/full-skill-archive-20260601.md`.
