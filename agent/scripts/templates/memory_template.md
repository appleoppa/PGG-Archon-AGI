# MEMORY.md — {profile}

> per-profile memory store | generated: {generated_at}

## 0. Identity

- profile: **{profile}**
- SOUL.md: {soul_line}
- skills: {skill_count}
- config providers: {provider_summary}

## 1. Memory model

- This file is the per-profile long-term memory store.
- It is bounded; if it grows beyond 256 KB, rotate to `MEMORY.archive/<date>.md`.
- It is **not** the conversation session log; session log lives in `sessions/`.

## 2. Topics to track (suggested)

- Recurring case types and their outcome patterns.
- Cross-department handoffs (which PGG partner did what).
- Hard rules the user has corrected in this profile's domain.
- Provider availability changes (Claude 403, DeepSeek empty content, etc.).
- Skills added/removed and the rationale.

## 3. Anti-patterns

- Do not paste raw LLM transcripts here.
- Do not store secrets.
- Do not overwrite this file with placeholder text.
