"""PGG Archon — ResearchExtractionSurface/v1.

Absorbs the useful read-only research extraction pattern from:
- APEX-AGI/omega-agi/research/src/extractor.rs
- APEX-AGI/omega-agi/research/src/reporter.rs
- APEX-AGI/omega-agi/research/src/knowledge.rs

This module does not browse the web, fetch URLs, call models, write files,
write genes, create background tasks, or claim AGI completion. It only turns
caller-supplied source snippets into a bounded extraction report: summary,
key points, relevance score, report preview, and concept graph counters.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

SURFACE_VERSION = "PGGArchonResearchExtractionSurface/v1"
SURFACE_SOURCE = "APEX-AGI omega-agi/research/src/{extractor,reporter,knowledge}.rs"
SURFACE_SOURCE_HASH = hashlib.sha256(SURFACE_SOURCE.encode("utf-8")).hexdigest()
SURFACE_LIMITS = {
    "max_sources": 20,
    "max_source_content_chars": 6000,
    "max_topic_chars": 200,
    "max_title_chars": 160,
    "max_url_chars": 300,
    "max_key_points": 10,
    "max_summary_chars": 1200,
    "max_report_preview_chars": 3000,
    "min_sentence_chars": 20,
    "max_sentence_chars": 500,
}
URL_HASH_SALT = f"{SURFACE_VERSION}:url-hash:v1"

_SENTENCE_SPLIT_RE = re.compile(r"[.!?。！？]\s*")
_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{2,}")


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    content: str

    @property
    def word_count(self) -> int:
        return len(_TOKEN_RE.findall(self.content))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "title": self.title[: SURFACE_LIMITS["max_title_chars"]],
            "url_hash": hashlib.sha256((URL_HASH_SALT + ":" + self.url).encode("utf-8")).hexdigest() if self.url else "",
            "word_count": self.word_count,
        }


@dataclass(frozen=True)
class ResearchExtraction:
    topic: str
    summary: str
    key_points: list[str]
    relevance: float
    word_count: int
    source_count: int
    concept_count: int
    insights: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _safe_text(value: Any, limit: int = 2000) -> str:
    return str(value or "").strip()[:limit]


def _topic_terms(topic: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(topic) if len(t) >= 2]


def _source_from_mapping(item: Mapping[str, Any]) -> ResearchSource:
    return ResearchSource(
        title=_safe_text(item.get("title") or item.get("name"), SURFACE_LIMITS["max_title_chars"]) or "untitled",
        url=_safe_text(item.get("url") or item.get("source") or item.get("id"), SURFACE_LIMITS["max_url_chars"]),
        content=_safe_text(item.get("content") or item.get("text") or item.get("snippet"), SURFACE_LIMITS["max_source_content_chars"]),
    )


def normalize_research_sources(sources: Sequence[Mapping[str, Any]] | None) -> list[ResearchSource]:
    normalized: list[ResearchSource] = []
    for item in _as_sequence(sources):
        if isinstance(item, Mapping):
            src = _source_from_mapping(item)
            if src.content:
                normalized.append(src)
    return normalized[: SURFACE_LIMITS["max_sources"]]


def score_relevance(text: str, topic: str) -> float:
    terms = _topic_terms(topic)
    if not terms:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for term in terms if term in text_lower)
    return min(1.0, hits / len(terms))


def extract_key_points(topic: str, sources: Sequence[ResearchSource], *, max_points: int | None = None) -> list[str]:
    terms = _topic_terms(topic)
    points: list[str] = []
    seen: set[str] = set()
    min_chars = SURFACE_LIMITS["min_sentence_chars"]
    max_chars = SURFACE_LIMITS["max_sentence_chars"]
    for source in sources:
        for raw_sentence in _SENTENCE_SPLIT_RE.split(source.content):
            sentence = raw_sentence.strip()
            if len(sentence) < min_chars:
                continue
            lower = sentence.lower()
            if terms and not any(term in lower for term in terms):
                continue
            compact = re.sub(r"\s+", " ", sentence)[:max_chars]
            key = compact.lower()
            if key not in seen:
                seen.add(key)
                points.append(compact)

    def relevance_key(point: str) -> tuple[int, int]:
        lower = point.lower()
        return (sum(1 for term in terms if term in lower), len(point))

    points.sort(key=relevance_key, reverse=True)
    cap = max_points if max_points is not None else SURFACE_LIMITS["max_key_points"]
    return points[:cap]


def build_concept_insights(topic: str, key_points: Sequence[str]) -> tuple[int, list[str]]:
    topic_terms = set(_topic_terms(topic))
    concept_counts: dict[str, int] = {}
    for point in key_points:
        for token in _TOKEN_RE.findall(point.lower()):
            if len(token) <= 3 or token in topic_terms:
                continue
            concept_counts[token] = concept_counts.get(token, 0) + 1
    top = sorted(concept_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    insights = [f"Concept '{concept}' appears in {count} extracted point(s)" for concept, count in top if count >= 1]
    return len(concept_counts), insights[:5]


def generate_report_preview(topic: str, extraction: ResearchExtraction, sources: Sequence[ResearchSource], *, fmt: str = "markdown") -> str:
    fmt = (fmt or "markdown").lower()
    cap = SURFACE_LIMITS["max_report_preview_chars"]
    if fmt == "json":
        payload = {
            "topic": extraction.topic,
            "summary": extraction.summary,
            "key_points": extraction.key_points[:5],
            "relevance": extraction.relevance,
            "word_count": extraction.word_count,
            "sources": [source.to_public_dict() for source in sources[:5]],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)[:cap]
    if fmt == "text":
        lines = [f"RESEARCH EXTRACTION: {topic}", f"Sources: {len(sources)}", f"Relevance: {extraction.relevance:.2f}", "", extraction.summary, "", "KEY POINTS:"]
        lines.extend(f"{i + 1}. {p}" for i, p in enumerate(extraction.key_points[:5]))
        return "\n".join(lines)[:cap]
    lines = [f"# Research Extraction: {topic}", "", f"- Sources: {len(sources)}", f"- Relevance: {extraction.relevance:.2f}", f"- Word count: {extraction.word_count}", "", "## Summary", extraction.summary, "", "## Key Points"]
    lines.extend(f"{i + 1}. {p}" for i, p in enumerate(extraction.key_points[:5]))
    return "\n".join(lines)[:cap]


def build_pgg_archon_research_extraction_surface(
    *,
    topic: str = "",
    sources: Sequence[Mapping[str, Any]] | None = None,
    report_format: str = "markdown",
) -> dict[str, Any]:
    clean_topic = _safe_text(topic, SURFACE_LIMITS["max_topic_chars"])
    normalized_sources = normalize_research_sources(sources)
    total_words = sum(src.word_count for src in normalized_sources)

    if not clean_topic:
        extraction = ResearchExtraction(
            topic="",
            summary="No research topic supplied.",
            key_points=[],
            relevance=0.0,
            word_count=total_words,
            source_count=len(normalized_sources),
            concept_count=0,
            insights=[],
        )
        status = "WATCH"
        warnings = ["ResearchTopicMissing"]
    elif not normalized_sources:
        extraction = ResearchExtraction(
            topic=clean_topic,
            summary=f"No caller-supplied sources available for '{clean_topic}'.",
            key_points=[],
            relevance=0.0,
            word_count=0,
            source_count=0,
            concept_count=0,
            insights=[],
        )
        status = "WATCH"
        warnings = ["ResearchSourcesMissing"]
    else:
        points = extract_key_points(clean_topic, normalized_sources)
        relevance = min(1.0, sum(score_relevance(src.content, clean_topic) for src in normalized_sources) / max(len(normalized_sources), 1))
        summary = ". ".join(points[:3]) if points else f"Research on '{clean_topic}' processed {len(normalized_sources)} source(s) with {total_words} token(s)."
        concept_count, insights = build_concept_insights(clean_topic, points)
        extraction = ResearchExtraction(
            topic=clean_topic,
            summary=summary[: SURFACE_LIMITS["max_summary_chars"]],
            key_points=points,
            relevance=relevance,
            word_count=total_words,
            source_count=len(normalized_sources),
            concept_count=concept_count,
            insights=insights,
        )
        status = "PASS" if points and relevance > 0 else "WATCH"
        warnings = [] if status == "PASS" else ["LowResearchRelevanceOrNoKeyPoints"]

    preview = generate_report_preview(clean_topic or "untitled", extraction, normalized_sources, fmt=report_format)
    report = {
        "schema": SURFACE_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "source": SURFACE_SOURCE,
        "source_hash": SURFACE_SOURCE_HASH,
        "limits": dict(SURFACE_LIMITS),
        "language_assumption": "ASCII/CJK token regex; sentence split on .!?。！？; non-Latin punctuation may produce shorter sentences and trigger LowResearchRelevanceOrNoKeyPoints — supply pre-segmented snippets if needed.",
        "topic": clean_topic,
        "source_count": len(normalized_sources),
        "word_count": extraction.word_count,
        "relevance": extraction.relevance,
        "key_point_count": len(extraction.key_points),
        "concept_count": extraction.concept_count,
        "warnings": warnings,
        "extraction": extraction.to_dict(),
        "public_sources": [src.to_public_dict() for src in normalized_sources[:10]],
        "report_format": report_format,
        "report_preview": preview,
        "side_effects": "read_only_report",
        "boundary": "No web browsing, network fetch, model call, file write, gene write, daemon start, or AGI completion claim is performed; only caller-supplied snippets are processed.",
        "agi_completion_claim": False,
    }
    report["surface_hash"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return report


__all__ = [
    "SURFACE_VERSION",
    "SURFACE_SOURCE_HASH",
    "SURFACE_LIMITS",
    "URL_HASH_SALT",
    "ResearchSource",
    "ResearchExtraction",
    "normalize_research_sources",
    "score_relevance",
    "extract_key_points",
    "build_concept_insights",
    "generate_report_preview",
    "build_pgg_archon_research_extraction_surface",
]
