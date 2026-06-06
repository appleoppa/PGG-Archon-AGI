---
name: apple-legal-research
version: "1.0.0"
description: 法律检索专家：法规、案例、文献
metadata:
  {
    "openclaw": {
      "requires": { "env": [] },
      "capabilities": ["reasoning", "web_search", "file_read"],
      "evolution": {
        "enabled": true,
        "version": "1.0.0"
      }
    },
    "author": "苹果哥",
    "category": "legal",
    "tags": ["法律检索", "法规", "案例", "学术", "检索报告"]
  }
---

# Apple Legal Research — Compact

## Trigger

Use for statutes, judicial interpretations, guiding cases, similar cases, legal opinions, issue research and authority verification.

## Local-first rule

For Chinese law, search local official legal KB first when available. Use external public sources only as supplement/cross-check. Do not let external samples replace local official corpus.

## Workflow

1. Convert facts into legal issues and keywords.
2. Search laws/articles/cases with local-first tool.
3. Verify article number, effective status, authority level and applicability.
4. Extract rule → elements → application → uncertainty.
5. Return concise legal basis with source fields.

## Output

`issue`, `rule`, `source`, `article/case`, `application`, `limits`, `need_more_facts`.

## Reference

Full research patterns archived at `references/full-skill-archive-20260601.md`.
