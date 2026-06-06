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

# PDF & Document Extraction

For DOCX: use `python-docx` (parses actual document structure, far better than OCR).
For PPTX: see the `powerpoint` skill (uses `python-pptx` with full slide/notes support).
This skill covers **PDFs and scanned documents**.

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | pytesseract+pdf2image (~50MB) | marker-pdf (~3-5GB) |
|---------|-----------------|--------------------------------|---------------------|
| **Text-based PDF** | ✅ | ❌ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (100+ langs via tesseract) | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ❌ (raw text only) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ❌ | ✅ |
| **Code blocks** | ❌ | ❌ | ✅ |
| **Forms** | ❌ | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ❌ | ✅ |
| **Reading order detection** | ❌ | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ❌ | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ | ✅ |
| **EPUB** | ✅ | ❌ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ❌ (plain text only) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~50MB (tesseract binary + pytesseract + pdf2image + pillow) | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~2-10s/page (CPU) | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Decision tree**:
1. Use **pymupdf** for text-based PDFs (no OCR needed) — instant, zero deps
2. Use **pytesseract+pdf2image** when you need OCR but marker-pdf is not installed or disk space is tight (~50MB vs 3-5GB). Falls short on tables, equations, reading order, complex layouts.
3. Use **marker-pdf** for high-quality OCR with layout, equations, tables, forms — but needs 3-5GB free disk and first-run model download.

---

## 轻量级图片 OCR（tesseract CLI — vision 不可用时的回退）

当模型不支持图片输入（如 vision_analyze 返回 400）时，用 tesseract CLI 直接从图片文件提取文字。

### 前置检查

```bash
which tesseract
tesseract --list-langs | grep chi_sim  # 确认中文字库
# 如缺失（macOS）：brew install tesseract-lang
```

### 执行 OCR

```bash
tesseract /path/to/image.jpg /tmp/output -l chi_sim
```

**关键陷阱**：tesseract 自动加 `.txt` 后缀，实际文件是 `/tmp/output.txt` 而非 `/tmp/output`。读取时注意：

```
tesseract img.jpg /tmp/t -l chi_sim
# → 文件在 /tmp/t.txt，不是 /tmp/t
# 如用 read_file 读 /tmp/t 提示不存在，试试 /tmp/t.txt
# 如仍不存在，试试 /tmp/t.txt.txt（双重扩展名）
```

### 多语言组合

```bash
tesseract img.jpg /tmp/out -l chi_sim+eng   # 中英文
tesseract img.jpg /tmp/out -l jpn            # 日文
tesseract img.jpg /tmp/out -l kor            # 韩文
```

### PSM 模式（Page Segmentation Mode）

| PSM | 模式 | 适用场景 |
|-----|------|---------|
| 3 | Fully automatic page layout, no OSD | 默认，通用 |
| 4 | Assume single column of text of variable sizes | 长文本块 |
| 6 | Single uniform block of text | 单一文本区域 |
| 11 | Sparse text. Find as much text as possible in no particular order | 稀疏文本、混杂文档 |
| 12 | Sparse text with OSD | 稀疏+方向检测 |

**实测结论（法律文档）**：PSM 6 在大多数情况下效果最佳；PSM 11 适合低质量扫描。

### pdftoppm 替代 pdf2image

当 pdf2image 在 `execute_code` 中不可用或 buffer 传递有问题时，用 pdftoppm 直接生成图片文件：

```bash
# 在 terminal() 中执行（不是 execute_code）
pdftoppm -r 400 -png -l 1 input.pdf page  # 输出 page-1.png
tesseract page-1.png stdout -l chi_sim+eng --psm 6
```

**组合命令（单行）**：
```bash
pdftoppm -r 400 -png -l 1 input.pdf /tmp/p && tesseract /tmp/p-1.png stdout -l chi_sim+eng --psm 6
```

关键参数：`-r 400`（必须 400 DPI，300 会导致中文 OCR 失败）；`-l 1`（只处理第 1 页）；`-png`（无损格式）。

### 文本型 vs 扫描型 PDF 决策树

1. 先用 `pdftotext -layout input.pdf -` 试探
2. 如果返回 >10 个中文字符 → 文本型 PDF，用 pdftotext（100% 准确）
3. 如果返回 <10 个中文字符 → 大概率扫描型，用 pdftoppm + tesseract（400 DPI，PSM 6）
4. 如果 tesseract 返回 <5 个中文字符 → 可能是低质量扫描，尝试 PSM 11 或人工审核

**Phase 211 教训**：对扫描型 PDF 使用 pdftotext 会误判为"工具失败"。正确方法是先试探再决定工具。

### 适用场景

| 场景 | 推荐 |
|------|------|
| 模型不支持 vision，需读截图文字 | ✅ tesseract CLI |
| 清晰截图/聊天记录/文档 | ✅ 效果良好 |
| 手写体/印章/表格/水印 | ⚠️ 效果差，需人工确认 |

### 完整工作流

```
vision_analyze 失败 → tesseract img1.jpg /tmp/t1.txt -l chi_sim
                   → tesseract img2.jpg /tmp/t2.txt -l chi_sim
                   → 读取输出（注意 .txt 后缀）
                   → 整合文字，标注文件名+行号溯源
```

---

## pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm
```

**Via helper script**:
```bash
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

**Inline**:
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

---

## Lightweight OCR (pytesseract + pdf2image)

Use this when pymupdf returns blank pages (CamScanner, phone scans, image-based PDFs) but marker-pdf is too heavy or not installed. Requires `tesseract` binary + Python packages:

```bash
# Install tesseract binary (macOS)
brew install tesseract tesseract-lang  # includes Chinese, Japanese, etc.

# Python packages
pip install pytesseract pdf2image pillow
```

**Basic usage**:
```python
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path('scanned.pdf', dpi=300)
for i, img in enumerate(images):
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
    print(f'--- Page {i+1} ---')
    print(text)
```

**Common language codes**: `chi_sim` (Simplified Chinese), `chi_tra` (Traditional), `jpn`, `kor`, `eng`, `fra`, `deu`. Combine with `+`: `chi_sim+eng`, `jpn+eng`.

**Critical DPI requirement for Chinese legal documents**: Phase 212 proved that 300 DPI gives 0 Chinese characters output on scanned PDFs; **400 DPI is required** for tesseract chi_sim+eng to work on Chinese legal documents. Use `-r 400` in pdftoppm, not 150/200/300.

**execute_code sandbox isolation**: The `execute_code` tool uses a sandboxed `/tmp` that does NOT persist to the host `/tmp`. When you run `pdftoppm` or tesseract in `execute_code`, the generated files are invisible to host tools and vice versa. tesseract will error with "failed to open locally". **For all PDF→image→OCR workflows, use `terminal()` directly on host, NOT `execute_code()`.**

**pytesseract from execute_code fails**: `pdf2image.convert_from_path()` + `pytesseract.image_to_string()` inside `execute_code()` will silently return 0 characters because the image buffer is in the sandbox filesystem. If you must use Python for OCR, write the image to a host-visible path first via `terminal()`, then run tesseract via `terminal()`.
- Tesseract works best on clean, high-contrast scans. Noisy backgrounds, watermarks, or handwriting degrade accuracy significantly.
- No layout preservation — text comes out line-by-line, tables as jumbled rows. For structured documents, prefer marker-pdf.
- Chinese OCR requires `tesseract-lang` (or `tesseract-ocr-chi-sim` on Linux) for the language data files.
- Check availability: `python3 -c "import pytesseract; import pdf2image; print('ready')"`

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

pymupdf handles these natively — use `execute_code` or inline Python:

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

```python
# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

```python
# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

No extra dependencies needed — pymupdf covers split, merge, search, and text extraction in one package.

---

## Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- **pytesseract+pdf2image** is the lightweight OCR fallback when marker-pdf is too heavy (~50MB vs 3-5GB). Good for basic OCR on clean scans. Bad for tables, equations, complex layouts.
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)
