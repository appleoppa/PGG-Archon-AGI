#!/usr/bin/env python3
"""Build the initial PGG legal QA golden dataset from local sources only.

Inputs are deterministic local SQLite DBs when present, plus the existing local
text legal/case library and selected case-work markdowns. No LLM/network calls.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

HOME = Path.home()
OUT = HOME / ".hermes/data/golden/legal_qa_v1.jsonl"
DB_CANDIDATES = [
    HOME / ".hermes/workspace/04_knowledge/开智/法规库/SQLite/法律法规.db",
    HOME / ".hermes/workspace/04_knowledge/开智/法规库/SQLite/指导案例.db",
]
LAW_TXT_ROOT = HOME / ".hermes/workspace/04_knowledge/智库/法律法规库"
CASE_TXT_ROOT = HOME / ".hermes/workspace/04_knowledge/智库/案例库"
CMS_ROOT = HOME / ".hermes/workspace/苹果中枢办案库"

CATEGORY_KEYWORDS = [
    ("刑法", ["刑法", "刑事", "犯罪", "公诉", "逮捕", "审查起诉", "量刑", "辩护", "交通肇事", "有毒有害食品", "贪污", "受贿"]),
    ("行政", ["行政", "行政诉讼", "行政机关", "政府", "许可", "处罚", "复议", "国家赔偿"]),
    ("程序", ["程序", "诉讼", "管辖", "上诉", "再审", "执行", "仲裁", "起诉期限", "缺席审判", "受理"]),
    ("证据", ["证据", "证明", "质证", "鉴定", "举证", "事实证据", "材料", "调取"]),
    ("民法", ["民法", "民事", "合同", "侵权", "赔偿", "物业", "劳动", "工伤", "保险", "继承", "婚姻", "物权", "债权", "违约"]),
]

PREFERRED_LAW_PATTERNS = [
    "中华人民共和国劳动合同法_20121228.txt",
    "中华人民共和国劳动法_20181229.txt",
    "中华人民共和国社会保险法_20181229.txt",
    "工伤保险条例_20101220.txt",
    "最高人民法院关于审理劳动争议案件适用法律问题的解释（一）_20201229.txt",
    "最高法关于审理道路交通事故损害赔偿案件适用法律若干问题的解释二_法释〔2026〕9号_20260506.txt",
    "最高人民法院_最高人民检察院关于适用刑事缺席审判程序若干问题的规定_20260521.txt",
    "最高人民法院关于适用行政诉讼起诉期限若干问题的解释_法释〔2026〕3号_20260430.txt",
    "物业管理条例.txt",
    "中华人民共和国劳动争议调解仲裁法_20071229.txt",
]


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=enc, errors="ignore")
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def clean(s: str) -> str:
    s = s.replace("\u200f", "").replace("&nbsp;", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n+", "\n", s)
    return s.strip()


def category_for(text: str, path: Path | None = None) -> str:
    blob = text + (" " + str(path) if path else "")
    for category, kws in CATEGORY_KEYWORDS:
        if any(kw in blob for kw in kws):
            return category
    return "民法"


def law_name_from_path(path: Path) -> str:
    return re.sub(r"_\d{8}$", "", path.stem)


def iter_preferred_law_files() -> Iterable[Path]:
    yielded: set[Path] = set()
    if LAW_TXT_ROOT.exists():
        for pattern in PREFERRED_LAW_PATTERNS:
            for p in LAW_TXT_ROOT.rglob(pattern):
                if p not in yielded:
                    yielded.add(p)
                    yield p
        for p in sorted(LAW_TXT_ROOT.rglob("*.txt")):
            if p not in yielded:
                yielded.add(p)
                yield p


def extract_law_articles(path: Path) -> list[dict]:
    text = clean(read_text(path))
    law_name = law_name_from_path(path)
    items: list[dict] = []
    # Match Article headings and body until next Article. Keep concise but faithful.
    pattern = re.compile(r"(?m)(第[一二三四五六七八九十百零〇0-9]+条)\s*([^\n]+(?:\n(?!第[一二三四五六七八九十百零〇0-9]+条).+)*)")
    for m in pattern.finditer(text):
        article_no = m.group(1)
        body = clean(m.group(2)).replace("\n", " ")
        if len(body) < 18 or "来源说明" in body:
            continue
        if len(body) > 220:
            body = body[:220].rstrip("，；、。") + "。"
        source = f"{law_name}{article_no}"
        question = f"{source}的核心规则是什么？"
        items.append({
            "question": question,
            "expected": f"{source}规定：{body}",
            "category": category_for(law_name + body, path),
            "source": source,
        })
    return items


def extract_guiding_case(path: Path) -> dict | None:
    text = clean(read_text(path))
    title = ""
    for line in text.splitlines()[:8]:
        line = clean(line)
        if line and not line.startswith("关键词"):
            title = (title + " " + line).strip()
    m_no = re.search(r"指导案例\s*([0-9]+)号", text)
    m_point = re.search(r"裁判要点\s*(.*?)\s*(相关法条|基本案情|裁判结果|裁判理由)", text, re.S)
    if not (m_no and m_point):
        return None
    point = clean(m_point.group(1)).replace("\n", " ")
    if len(point) < 20:
        return None
    if len(point) > 240:
        point = point[:240].rstrip("，；、。") + "。"
    source = f"指导案例{m_no.group(1)}号"
    question = f"{source}的裁判要点是什么？"
    return {
        "question": question,
        "expected": f"{source}（{title}）裁判要点：{point}",
        "category": category_for(text, path),
        "source": source,
    }


def iter_guiding_case_files() -> Iterable[Path]:
    if not CASE_TXT_ROOT.exists():
        return []
    return sorted(CASE_TXT_ROOT.rglob("指导案例*.txt"))


def extract_cms_items() -> list[dict]:
    items: list[dict] = []
    if not CMS_ROOT.exists():
        return items
    for p in sorted(CMS_ROOT.rglob("*.md")):
        name = p.name
        if any(skip in str(p) for skip in ["_backups", ".DS_Store"]):
            continue
        if not any(key in name for key in ["法律依据", "证据", "总结", "分析", "意见", "起诉状", "上诉状"]):
            continue
        text = clean(read_text(p))
        refs = []
        for pat in [r"《[^》]{2,40}》第[一二三四五六七八九十百零〇0-9]+条", r"第[一二三四五六七八九十百零〇0-9]+条"]:
            refs.extend(re.findall(pat, text))
        refs = list(dict.fromkeys(refs))[:3]
        if not refs:
            continue
        # Use a nearby sentence that contains the first reference, avoiding invented summaries.
        first = refs[0]
        sentence = ""
        for seg in re.split(r"[。；\n]", text):
            if first in seg and 20 <= len(seg) <= 240:
                sentence = clean(seg)
                break
        if not sentence:
            continue
        source = f"本地办案库：{p.name}"
        items.append({
            "question": f"本地案件材料《{p.stem}》引用的关键法律依据是什么？",
            "expected": f"该材料引用{', '.join(refs)}；原文摘录：{sentence}。",
            "category": category_for(text, p),
            "source": source,
        })
        if len(items) >= 8:
            break
    return items


def db_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    conn = sqlite3.connect(path)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            text_cols = [c for c in cols if any(k in c.lower() for k in ["title", "name", "content", "text", "body", "article", "source"])]
            if not text_cols:
                continue
            q = f"SELECT {', '.join(text_cols)} FROM {table} LIMIT 20"
            for rec in conn.execute(q):
                parts = [clean(str(x)) for x in rec if x]
                blob = " ".join(parts)
                if len(blob) < 30:
                    continue
                expected = blob[:240].rstrip("，；、。") + ("。" if len(blob) > 240 else "")
                source = f"{path.name}:{table}"
                rows.append({
                    "question": f"本地SQLite法规库条目（{source}）的核心内容是什么？",
                    "expected": expected,
                    "category": category_for(blob),
                    "source": source,
                })
    finally:
        conn.close()
    return rows


def dedupe(items: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = item["question"] + "\n" + item["expected"][:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def main() -> None:
    collected: list[dict] = []
    for db in DB_CANDIDATES:
        collected.extend(db_rows(db))
    for path in iter_preferred_law_files():
        collected.extend(extract_law_articles(path))
        if len(collected) >= 34:
            break
    for path in iter_guiding_case_files():
        item = extract_guiding_case(path)
        if item:
            collected.append(item)
        if len(collected) >= 46:
            break
    collected.extend(extract_cms_items())
    collected = dedupe(collected)

    # Balance to exactly 50 using local law/case text if available.
    if len(collected) < 50:
        for path in iter_preferred_law_files():
            for item in extract_law_articles(path):
                collected.append(item)
                collected = dedupe(collected)
                if len(collected) >= 50:
                    break
            if len(collected) >= 50:
                break
    if len(collected) < 50:
        raise SystemExit(f"only generated {len(collected)} items; need 50")

    final = collected[:50]
    for idx, item in enumerate(final, 1):
        item["id"] = f"PGG-GOLDEN-{idx:03d}"
        # enforce field order
        final[idx - 1] = {
            "id": item["id"],
            "question": item["question"],
            "expected": item["expected"],
            "category": item["category"],
            "source": item["source"],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for item in final:
            f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"schema": "pgg-golden-builder/v1", "output": str(OUT), "total": len(final)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
