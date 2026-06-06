---
name: apex-book-to-skill
version: 1.0.0
description: 超级进化16 过目不忘 book-to-skill 管线。将书籍/文档解析为可追溯 skill 草案、懒加载 manifest、证据地图。
metadata:
  source: /Users/appleoppa/Desktop/超级进化16-激活神技能过目不忘 .md
  formula: ApexBookSkill = DoclingParse × SkillStruct × LazyLoad × MemLLM × ParallelAgent
---

# APEX Book to Skill — Compact

## Trigger

Use when turning books/docs into traceable skill drafts, evidence maps and reusable procedures.

## Workflow

1. Parse source into claims, procedures and examples.
2. Keep provenance: page/chapter/path/hash.
3. Extract only actionable patterns.
4. Draft compact SKILL.md with references for long material.
5. Validate by applying to a real task or review.

## Reference

Full pipeline archived at `references/full-skill-archive-20260601.md`.
