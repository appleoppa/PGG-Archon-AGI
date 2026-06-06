# APEX Output Normalization Rules

## Learnable source directive

APEX premium native typography governance means: normalize chaotic model output into formal print-like document structure, then render with golden-ratio margins, refined spacing, dual multilingual serif fonts, matte warm paper background, low-saturation tone, and unified block components.

## Safe normalization order

1. Protect fenced code blocks, Markdown tables, legal exhibit quotations, poetry, and intentionally aligned text.
2. Remove trailing spaces and zero-width redundant characters outside protected blocks.
3. Collapse 3+ consecutive blank lines into 2 blank lines.
4. Normalize heading spacing: one blank line before and after major headings unless at document start.
5. Normalize list spacing: one item per line; preserve numbering and legal article references.
6. Normalize blockquote spacing: contiguous quoted lines remain in one quote block.
7. Remove decorative repeated punctuation unless it is part of evidence or user-provided title.
8. Preserve all substantive words, numbers, dates, case names, legal references, and citations.

## Do-not-touch zones

- fenced code blocks
- tables
- YAML/JSON/TOML frontmatter or config blocks
- quoted evidence excerpts requiring exact reproduction
- court/legal official formatting where format is prescribed
- ASCII diagrams or aligned columns

## Output contract

When applying this skill, state whether normalization was:

- `full`: rendered artifact was normalized and previewed/verified
- `text-only`: text was cleaned but not visually rendered
- `skipped`: official/legal/source fidelity prevented typographic changes

## Accessibility gates

- Body text must remain solid, high contrast.
- Gradient text is limited to display headings.
- Low-saturation palette must still pass practical readability.
- Responsive margins must not overflow narrow screens.
