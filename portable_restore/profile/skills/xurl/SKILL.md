---
name: xurl
description: X/Twitter操作：发帖、搜索、私信、媒体
version: 1.1.1
author: xdevplatform + openclaw + Hermes Agent
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [xurl]
metadata:
  hermes:
    tags: [twitter, x, social-media, xurl, official-api]
    homepage: https://github.com/xdevplatform/xurl
    upstream_skill: https://github.com/openclaw/openclaw/blob/main/skills/xurl/SKILL.md
---

# X/Twitter Operations — Compact

## Trigger

Use for X/Twitter posting, search, profile/media analysis, DMs, thread drafting, and media upload operations.

## Safety

Posting, replying, DMing, following/unfollowing, deleting, or liking are external side effects. Confirm target/content unless the user gave explicit instruction. Never fabricate that a post was sent; require API/tool result evidence.

## Workflow

1. Clarify whether the task is draft/search/read-only or write action.
2. For search/research, keep raw results external and summarize with links/IDs.
3. For posting, prepare concise draft; preserve user wording and hashtags.
4. For media, verify local file exists and upload result returns an ID/URL.
5. Report status, post URL/ID, or blocker.

## Output

Use fields: `status`, `action`, `target`, `id/url`, `evidence`, `blocker`.

## Reference

Full API patterns and examples archived at `references/full-skill-archive-20260601.md`.
