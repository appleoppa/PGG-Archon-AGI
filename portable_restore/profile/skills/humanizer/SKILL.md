---
name: humanizer
description: 文本人性化：去除AI味，增加真实语音
version: 2.5.1
author: Siqi Chen (@blader, https://github.com/blader/humanizer), ported by Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [writing, editing, humanize, anti-ai-slop, voice, prose, text]
    category: creative
    homepage: https://github.com/blader/humanizer
    related_skills: [songwriting-and-ai-music]
---

# Humanizer — Compact

## Trigger

Use when the user asks to humanize, de-AI, rewrite, polish, or make prose sound natural. Do not use for legal/factual changes unless separately requested.

## Operating rule

Preserve meaning and factual claims. Change voice, rhythm, transitions, specificity and texture. If legal/technical accuracy matters, keep terms exact and avoid adding unsupported facts.

## Fast workflow

1. Identify audience, medium, tone and constraints.
2. Remove AI patterns: generic openings, excessive balance, thesis-signposting, inflated significance, repetitive triads, sterile transitions.
3. Add human texture: concrete nouns, varied sentence length, natural imperfection, viewpoint, pacing, and lived details.
4. Keep structure readable; do not over-casualize professional/legal text.
5. Return only the rewritten text unless the user asks for explanation.

## Voice calibration

If the user provides a sample, mirror:

- sentence length and punctuation habits;
- directness vs warmth;
- vocabulary level;
- humor/skepticism/authority level;
- paragraph density.

## Common AI patterns to remove

- “It is important to note...” / “In today’s rapidly evolving...”
- overuse of “not only... but also...”
- vague “underscores the importance/significance” claims;
- stacked abstractions instead of examples;
- every paragraph ending with a neat moral;
- promotional language when neutral writing is needed.

## Output contract

- For short text: return polished version directly.
- For long text: preserve headings and paragraph order unless asked to restructure.
- For sensitive/legal material: mark assumptions and avoid inventing facts.

## Reference

Full pattern library and examples are archived at:

- `references/full-skill-archive-20260601.md`

Load the archive only when detailed before/after examples or the full anti-pattern catalogue is needed.
