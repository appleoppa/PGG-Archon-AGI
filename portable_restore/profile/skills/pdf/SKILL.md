---
name: pdf
description: PDF读取、合并、拆分、OCR、水印、加密
license: Proprietary. LICENSE.txt has complete terms
---

# PDF — Compact

## Trigger

Use to read, merge, split, OCR, watermark, encrypt/decrypt, extract images, or inspect PDF metadata.

## Workflow

1. Verify file exists and identify whether text layer exists.
2. Use direct text extraction before OCR.
3. Preserve page ranges and filenames carefully.
4. For edits/merge/split, write to a new output path unless overwrite is explicitly requested.
5. Verify output exists, page count, and sample text/pages.

## Pitfalls

- Scanned PDFs may return empty text.
- OCR success requires non-empty extracted text or visual sample check.
- Paths with spaces/Chinese need safe quoting or Python subprocess.

## Reference

Full command/tool examples archived at `references/full-skill-archive-20260601.md`.
