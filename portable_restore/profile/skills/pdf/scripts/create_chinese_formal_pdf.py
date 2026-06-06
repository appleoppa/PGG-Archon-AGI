# -*- coding: utf-8 -*-
"""
Reusable starter for creating formal Chinese PDFs with ReportLab and automatic
post-generation verification. Copy and adapt content/sections before running.

Key points:
- Use ReportLab CID font STSong-Light for selectable/extractable Chinese text.
- Do not rely on PyMuPDF insert_textbox with TTC fonts when text extraction must
  be verified; it may render visually but extract as question marks.
- Verify file existence, A4 page size, page count, empty pages, and required terms.
"""
from pathlib import Path
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import fitz  # PyMuPDF, for verification only

OUT = Path.home() / "Desktop" / "正式中文报告.pdf"
TITLE = "正式中文报告"
REQUIRED_TERMS = ["核心结论", "阶段速览", "主要依据"]

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
FONT = "STSong-Light"
W, H = A4
blue = colors.HexColor("#17365D")
gold = colors.HexColor("#B08A2E")
light_blue = colors.HexColor("#EEF5FB")
gray = colors.HexColor("#555555")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CNTitle", fontName=FONT, fontSize=24, leading=32,
                          alignment=TA_CENTER, textColor=colors.white))
styles.add(ParagraphStyle(name="CNSubTitle", fontName=FONT, fontSize=14, leading=21,
                          alignment=TA_CENTER, textColor=colors.HexColor("#FFF2CC")))
styles.add(ParagraphStyle(name="CNH1", fontName=FONT, fontSize=14, leading=20,
                          textColor=blue, backColor=light_blue,
                          borderPadding=(6, 8, 6, 8), spaceBefore=10, spaceAfter=8))
styles.add(ParagraphStyle(name="CNBody", fontName=FONT, fontSize=10.8, leading=17,
                          firstLineIndent=21.6, alignment=TA_LEFT, spaceAfter=6))
styles.add(ParagraphStyle(name="CNBodyNoIndent", fontName=FONT, fontSize=10.8,
                          leading=17, alignment=TA_LEFT, spaceAfter=6))

def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def P(text: str, style):
    return Paragraph(esc(text), style)

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(blue)
    canvas.rect(0, H - 16 * mm, W, 16 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT, 9)
    canvas.drawString(20 * mm, H - 10 * mm, TITLE)
    canvas.setStrokeColor(colors.HexColor("#CCCCCC"))
    canvas.line(20 * mm, 14 * mm, W - 20 * mm, 14 * mm)
    canvas.setFillColor(gray)
    canvas.drawRightString(W - 20 * mm, 8 * mm, f"第 {doc.page} 页")
    canvas.restoreState()

story = []
cover = Table([
    [P(TITLE, styles["CNTitle"])],
    [P("实务说明与审查清单", styles["CNSubTitle"])],
], colWidths=[A4[0] - 40 * mm], rowHeights=[18 * mm, 12 * mm])
cover.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), blue),
    ("BOX", (0, 0), (-1, -1), 1.2, gold),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))
story += [cover, Spacer(1, 10 * mm)]
story += [P("核心结论", styles["CNH1"]),
          P("这里填写正式报告正文。中文应可复制、可检索、可提取。", styles["CNBody"]),
          P("阶段速览", styles["CNH1"]),
          P("可使用少量表格、蓝金配色、页眉页脚，避免花哨。", styles["CNBody"]),
          P("主要依据", styles["CNH1"]),
          P("这里填写法律依据、数据来源或核验提示。", styles["CNBodyNoIndent"])]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=20 * mm,
                        leftMargin=20 * mm, topMargin=24 * mm,
                        bottomMargin=20 * mm, title=TITLE, author="Hermes")
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

# Verification
result = {"path": str(OUT), "exists": OUT.exists(), "size_bytes": OUT.stat().st_size if OUT.exists() else 0}
if OUT.exists():
    pdf = fitz.open(OUT)
    text = "\n".join(page.get_text("text") for page in pdf)
    result.update({
        "pages": pdf.page_count,
        "metadata_title": pdf.metadata.get("title"),
        "text_chars": len(text),
        "contains_required_terms": {term: term in text for term in REQUIRED_TERMS},
        "page_sizes": [tuple(round(x, 2) for x in pdf[i].rect) for i in range(pdf.page_count)],
        "empty_pages": [i + 1 for i in range(pdf.page_count) if len(pdf[i].get_text("text").strip()) < 50],
    })
    pdf.close()
print(json.dumps(result, ensure_ascii=False, indent=2))
