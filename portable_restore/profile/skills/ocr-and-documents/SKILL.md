---
name: ocr-and-documents
description: 从PDF/扫描件提取文字
version: 2.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Documents, Research, Arxiv, Text-Extraction, OCR]
    related_skills: [powerpoint]
---

# OCR and Documents — Compact

## Trigger

Use to extract text from PDFs, scans, images, Word/Office files, or mixed document bundles.

## Workflow

1. Identify file type and whether text layer exists.
2. Try direct text extraction before OCR.
3. OCR only pages/images that need it.
4. Preserve page numbers and uncertain recognition.
5. Verify sample pages; do not treat empty OCR as success.

## Pitfalls

- `tesseract` installed does not mean usable OCR output.
- Scanned PDFs can return 0 chars from text extraction.
- Paths with Chinese/special chars may require Python subprocess with absolute paths.

## Output

Return extracted text path, page count, method, quality warnings, and verification sample.

## Reference

Full tool matrix and examples archived at `references/full-skill-archive-20260601.md`.
