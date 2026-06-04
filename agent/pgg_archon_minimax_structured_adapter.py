"""MiniMax structured-output adapter.

Normalizes MiniMax-M3 outputs that often include <think>...</think> before JSON.
Boundary: parsing adapter only; does not upgrade model verdicts or fabricate PASS.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ParseResult:
    schema: str
    ok: bool
    data: dict[str, Any] | None
    error: str | None
    visible_chars: int
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def parse_structured_json(text: str) -> ParseResult:
    raw = text or ""
    clean = strip_think(raw)
    candidates: list[str] = [clean]
    m = re.search(r"\{.*\}", clean, re.S)
    if m:
        candidates.append(m.group(0))
    # balanced scan fallback
    start = clean.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(clean[start:], start):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidates.append(clean[start : i + 1])
                        break
    for c in candidates:
        if not c.strip():
            continue
        try:
            parsed = json.loads(c)
            if isinstance(parsed, dict):
                return ParseResult(
                    schema="PGGArchonStructuredParse/v1",
                    ok=True,
                    data=parsed,
                    error=None,
                    visible_chars=len(raw),
                    boundary="Parser success only; does not validate truth or upgrade verdict.",
                )
        except Exception:
            pass
    return ParseResult(
        schema="PGGArchonStructuredParse/v1",
        ok=False,
        data=None,
        error="json_parse_failed",
        visible_chars=len(raw),
        boundary="Parser failure preserved; do not count as PASS.",
    )
