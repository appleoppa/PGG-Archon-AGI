---
name: arxiv
description: 按关键词/作者/分类搜索arXiv论文
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Arxiv, Papers, Academic, Science, API]
    related_skills: [ocr-and-documents]
---

# arXiv Research — Compact

## Trigger

Use to search arXiv by keyword, author, category, paper title, or to summarize/review papers.

## Workflow

1. Search targeted query; avoid broad dumps.
2. Select papers by relevance, recency, citations/venue signals if available, and abstract fit.
3. Read abstract first; fetch PDF only if needed.
4. Extract contribution, method, evidence, limits, and applicability.
5. Provide IDs/URLs and distinguish paper claims from your conclusions.

## Output

For each paper: `title`, `arXiv id`, `year`, `why relevant`, `core idea`, `limits`.

## Reference

Full API/query examples archived at `references/full-skill-archive-20260601.md`.
