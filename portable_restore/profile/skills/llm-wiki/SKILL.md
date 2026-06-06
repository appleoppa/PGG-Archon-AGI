---
name: llm-wiki
description: Karpathy LLM Wiki：构建/查询关联Markdown知识库
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative]
    category: research
    related_skills: [obsidian, arxiv]
---

# Karpathy LLM Wiki — Compact

## Trigger

Use when building or querying a lightweight Markdown knowledge base as an alternative/complement to RAG: research notes, project wiki, concept graph, source-grounded learning.

## Core architecture

Use three layers:

1. `SCHEMA.md` — domain, naming, frontmatter, link conventions.
2. Topic notes — atomic Markdown pages with sources and backlinks.
3. Index/Map pages — navigation, open questions, update log.

## Resume existing wiki

At session start, read only:

- `SCHEMA.md`
- root index/map
- one or two directly relevant topic pages

Do not load the whole wiki. Search filenames/content first, then read targeted windows.

## Add knowledge

1. Extract claim/source pairs.
2. Create/update the smallest relevant note.
3. Add backlinks and aliases.
4. Record uncertainty and TODOs.
5. Update index only if navigation changes.

## Query knowledge

- Search first.
- Read targeted pages.
- Answer with source-linked claims.
- If no source exists, say so and create a TODO rather than hallucinating.

## Reference

Full templates and examples are archived at:

- `references/full-skill-archive-20260601.md`
