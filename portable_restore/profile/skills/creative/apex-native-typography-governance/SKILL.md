---
name: apex-native-typography-governance
description: APEX 原生高级文档排版治理：黄金比例页边距、梯度标题层级、双语 serif 字体、暖纸低饱和色系、统一引用/列表/分隔线与模型输出排版净化。
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [typography, document-rendering, css, markdown, pdf, multilingual, apex]
---

# APEX Native Typography Governance

## Trigger

Use when polishing, rendering, designing, or normalizing high-end documents, Markdown/PDF/HTML reports, legal or research deliverables, presentation notes, and any user request mentioning APEX typography, premium native typography, golden proportion margins, gradient hierarchy, serif font architecture, matte warm paper, or formal printing logic.

## Core judgment

The user-provided directive is **learnable and reusable**. Treat it as a document aesthetic governance layer, not as vague decoration. Convert it into concrete style tokens, spacing rules, font stacks, block specifications, and a safe whitespace normalizer.

## APEX typography rules

1. **Golden proportion page margin**
   - Prefer asymmetric editorial margins using a golden-ratio feel: inner/top smaller, outer/bottom larger.
   - For responsive HTML, use `clamp()` instead of fixed margins to avoid narrow-screen clipping.
   - For printable pages, approximate with top 18–22mm, outer/bottom 28–36mm, inner 20–26mm unless a court/official format requires otherwise.

2. **Complete gradient text hierarchy**
   - Build hierarchy through size, weight, color, spacing, and restrained gradient accents.
   - Use gradients mainly for H1/H2 or cover/title elements; never reduce body readability.
   - Body text remains solid high-contrast ink color.

3. **Global kerning, line spacing, paragraph spacing**
   - Enable `font-kerning: normal`, `font-variant-ligatures: common-ligatures`, and slight letter-spacing only where useful.
   - Body line-height target: 1.58–1.72 for Chinese/English mixed documents.
   - Paragraph spacing should follow a stable vertical rhythm; avoid random blank lines.

4. **Dual multilingual serif font architecture**
   - Latin serif stack: `Cormorant Garamond`, `EB Garamond`, `Georgia`, `Times New Roman`, serif.
   - CJK serif stack: `Noto Serif SC`, `Source Han Serif SC`, `Songti SC`, `STSong`, serif.
   - Use `lang` selectors or CSS font stacks; never assume one font covers all scripts beautifully.

5. **Matte warm paper + low desaturated tone system**
   - Use warm paper background near `#faf7f1` / `#f7f1e8`.
   - Use low-saturation ink/accent colors: charcoal, warm brown, muted gold, dusty blue/green.
   - Check contrast for body text; low saturation must not mean low legibility.

6. **Unified quote block/list/divider specs**
   - Blockquote: subtle warm background, left border/accent, italic or serif emphasis only when readable.
   - Lists: consistent indentation, marker color, spacing between items.
   - Dividers: thin warm neutral line or gradient hairline; avoid heavy black rules.

7. **Automatic whitespace and model-output normalization**
   - Purge trailing spaces, repeated blank lines, invisible redundant characters, and chaotic list spacing.
   - Preserve code blocks, legal numbering, poetry, tables, and intentionally aligned text.
   - Normalize before rendering; do not rewrite legal meaning or substantive content.

8. **Formal printing typography logic**
   - Convert chaotic LLM output into clean sections, stable headings, restrained emphasis, and print-like spacing.
   - Prefer understated premium editorial aesthetics over flashy web effects.

## Workflow

1. Classify output target: mobile Markdown, HTML, PDF, PPT, legal document, research report, or article.
2. Apply normalization pass first: remove redundant whitespace while preserving semantic blocks.
3. Choose token set: page margin, font stack, size scale, line-height, paragraph spacing, palette, block styles.
4. Render or rewrite with APEX hierarchy: title → subtitle → section → body → metadata/footnote.
5. Verify readability: contrast, small-screen behavior, multilingual font fallback, no broken lists/tables/code blocks.
6. If producing code/CSS, include reusable tokens and avoid hardcoding one platform-only font.

## Chat output style for Apple Didi

When applying APEX to normal assistant replies, the goal is not decorative CSS but readable editorial structure:

- Prefer short sections with clear headings: `结论` → `证据` → `风险` → `下一步`.
- Avoid dense large tables unless comparison is genuinely easier in a table.
- Use stable whitespace and short paragraphs; do not compress many unrelated facts into one screen-filling block.
- Keep bullet lists selective: 3–7 important items beats exhaustive mechanical dumps.
- Put long paths/logs/commands behind concise evidence lines; only expand when the user asks or verification requires it.
- Preserve truth-state labels (`完整完成`, `部分完成`, `证据不足`, `未验证`) even while making the output visually cleaner.
- For mobile/Feishu-style reading, prefer fieldized prose over wide tables.

## Apple output preference layer

When reporting operational/audit/repair work to 苹果哥, apply APEX typography to the assistant's plain Markdown output, not only to generated documents:

- Prefer calm section hierarchy over large dense tables: `结论 → 已完成 → 证据 → 风险 → 下一步`.
- Use short paragraphs and restrained bullets; avoid screen-filling mechanical checklists unless the user asks for exhaustive logs.
- Keep evidence paths and command results, but compress them to the minimum verifiable handles.
- Use dividers sparingly; do not create visual noise with repeated table borders or overly long field lists.
- Preserve truth-state labels (`已完成`, `部分完成`, `未验证`, `已隔离`) while making the report legible.
- If a previous response was visually uncomfortable, immediately switch to this compact APEX report shape and save the preference in the governing skill.

## Conversational output style for 苹果哥

When the user is reading normal assistant replies rather than a rendered artifact, apply APEX as a **low-noise response contract**:

- Prefer short sections with breathable spacing: `结论` → `关键证据` → `风险` → `下一步`.
- Avoid large dense tables unless comparison is genuinely the clearest form; use field-style bullets instead.
- Keep paragraphs short and information-bearing; do not fill the screen with command transcripts or path dumps.
- Use stable list rhythm: 3–6 key bullets first, then details only when needed.
- Preserve verification discipline: improved typography must not soften uncertainty or make partial completion look final.
- For mobile/Feishu contexts, reduce visual complexity further: concise headings, short bullets, no wide tables.

## Boundaries and risks

- Do not apply decorative gradients to legal body text or official court-format documents where plain formatting is required.
- Do not purge whitespace inside code blocks, tables, quotes requiring exact reproduction, or evidence excerpts.
- Do not sacrifice accessibility for low-saturation aesthetics.
- Do not claim a document is professionally typeset unless it has been rendered or previewed.

## Verification contract

A complete application should report:

- `normalization`: what whitespace/model-output issues were fixed
- `layout`: margin/spacing/font system applied
- `blocks`: quote/list/divider consistency applied
- `accessibility`: contrast/readability checked or limitation stated
- `artifact`: rendered file path or rewritten document, if requested

## References

- `references/apex-typography-token-template.css`: reusable CSS token template.
- `references/apex-output-normalization-rules.md`: safe whitespace/model-output normalization rules.
