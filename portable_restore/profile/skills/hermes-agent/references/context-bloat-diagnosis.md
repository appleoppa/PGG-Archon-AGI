# Context Bloat — Diagnosis & Optimization

> How Hermes compiles its system prompt, why it can bloat to 100K+ tokens, and how to fix it.

## How System Prompt is Compiled

Hermes injects multiple sources into every turn's system prompt:

| Source | Loaded From | What It Contains |
|--------|-------------|-----------------|
| AGENTS.md | `~/.hermes/workspace/AGENTS.md` (via `build_context_files_prompt`) | Rules, workflow, team structure |
| MEMORY.md | `~/.hermes/memories/MEMORY.md` (via `MemoryStore.load_from_disk()`) | Persistent memory entries; separated by `§` |
| USER.md | `~/.hermes/memories/USER.md` (via `MemoryStore.load_from_disk()`) | User profile entries |
| Skill descriptions | All SKILL.md files' frontmatter `description` field | Injected as `<available_skills>` XML block |
| Tool schemas | Tool registry schemas | Full JSON function definitions |
| Personality text | `config.yaml` → `display.personality` | Inline personality string |

**Key detail:** The `MemoryStore` reads from `get_hermes_home() / "memories/"` — NOT from `~/.hermes/workspace/`. The snapshot is frozen at `load_from_disk()` time (agent init). Mid-session `memory()` tool calls update the file but do NOT change the running system prompt snapshot.

## Primary Bloat Sources

| Source | Typical Size | Fix |
|--------|-------------|-----|
| MEMORY.md duplicating AGENTS.md | 4-8K chars wasted | Strip to content NOT in AGENTS.md |
| USER.md duplicating AGENTS.md | 2-4K chars wasted | Same treatment |
| Skill descriptions (60+ skills) | 8-15K chars | Shorten to 20-50 char one-liners |
| Tool schemas | 30-50K chars | Not adjustable (built-in) |

## Diagnosis Steps

1. Read `~/.hermes/memories/MEMORY.md` and `~/.hermes/memories/USER.md`
2. Cross-check sections against `~/.hermes/workspace/AGENTS.md`
3. If same rule appears in ≥2 places, MEMORY.md/USER.md are the ones to trim (AGENTS.md is the canonical rule file)
4. Also check: are skill descriptions unnecessarily verbose?

## Optimization Guide

**For MEMORY.md / USER.md:**
- Remove any section that duplicates AGENTS.md (red lines, workflow steps, output rules, APEX tables, token discipline — all live in AGENTS.md)
- Keep only: user-specific preferences, system facts not in AGENTS.md, learning records, unique references
- Target: < 2,000 chars per file

**For skill descriptions:**
- Each skill's `description` in SKILL.md frontmatter is injected as-is
- Prefer 20-50 char descriptions (just enough to decide if the skill is relevant)
- Verbose 200-char descriptions with version info, multi-line marketing text all get loaded every turn

**Character limits (configurable):**
```python
MemoryStore(memory_char_limit=..., user_char_limit=...)
```
Defaults: 2200 (memory), 1375 (user). Check `config.yaml` → `memory.memory_char_limit` / `memory.user_char_limit`.

## Optimization Checklist

- [ ] MEMORY.md only contains facts NOT in AGENTS.md
- [ ] USER.md only contains user-specific preferences NOT in AGENTS.md
- [ ] No duplicate rules across AGENTS.md / MEMORY.md / USER.md
- [ ] Skill descriptions are short (one line each)
- [ ] Changes take effect on **next session** (snapshot frozen at init)
