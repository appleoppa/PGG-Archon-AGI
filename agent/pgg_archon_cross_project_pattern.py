"""
PGG Archon — CrossProjectPatternSurface/v1

Source: APEX-AGI omega_pipeline/cross_project_learning.py
Absorbed: 2026-05-28

Purpose: Cross-project experience extraction → desensitized pattern candidates.
         Provides a structured schema for pattern discovery without auto-ingesting
         full repositories or auto-writing to the gene database.

NOT:
  - Auto-scanning all projects on disk
  - Auto-writing to gene DB or mutation pipeline
  - Embedding/vector search of full codebases
"""

from __future__ import annotations
import re
import hashlib
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime
from enum import Enum


class PatternType(Enum):
    CODE = "code"
    TEST = "test"
    ERROR = "error"
    ARCHITECTURE = "architecture"


@dataclass
class Pattern:
    """A single extracted pattern candidate."""
    id: str
    pattern_type: str
    project: str
    source_file: str
    code_snippet: str
    description: str
    usage_count: int = 0
    success_rate: float = 0.0
    applicability: str = "medium"  # high / medium / low

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.pattern_type,
            "project": self.project,
            "source_file": self.source_file,
            "snippet": self.code_snippet[:120],
            "description": self.description,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "applicability": self.applicability,
        }


@dataclass
class PatternCandidate:
    """A cross-project pattern candidate ready for review."""
    pattern: Pattern
    source_project: str
    confidence: float
    similar_to_existing: List[str] = field(default_factory=list)
    should_promote: bool = False

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern.to_dict(),
            "source_project": self.source_project,
            "confidence": self.confidence,
            "similar_to": self.similar_to_existing,
            "should_promote": self.should_promote,
        }


@dataclass
class CrossProjectScanResult:
    """Result of a cross-project pattern scan."""
    projects_scanned: int
    files_scanned: int
    patterns_extracted: int
    candidates: List[PatternCandidate]
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "projects_scanned": self.projects_scanned,
            "files_scanned": self.files_scanned,
            "patterns_extracted": self.patterns_extracted,
            "candidates": [c.to_dict() for c in self.candidates],
            "errors": self.errors,
            "summary": {
                "by_type": self._by_type(),
                "promotable": sum(1 for c in self.candidates if c.should_promote),
            },
        }

    def _by_type(self) -> dict:
        counts = {}
        for c in self.candidates:
            t = c.pattern.pattern_type
            counts[t] = counts.get(t, 0) + 1
        return counts


# ── lightweight helpers (adapted, no DB/embedding dependency) ──

def _detect_lang(file_path: str) -> Optional[str]:
    ext = os.path.splitext(file_path)[1].lower()
    return {".rs": "rust", ".py": "python", ".js": "javascript", ".ts": "typescript"}.get(ext)


def _extract_signatures(content: str, lang: str) -> List[str]:
    if lang == "rust":
        return re.findall(r'(?:pub\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
    elif lang == "python":
        return re.findall(r'(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
    elif lang in ("javascript", "typescript"):
        return re.findall(r'(?:async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', content)
    return []


def _simple_hash(text: str, dims: int = 64) -> List[float]:
    """Deterministic hash-based embedding (no external deps)."""
    emb = [0.0] * dims
    for i, c in enumerate(text):
        emb[i % dims] += ord(c) * (i + 1)
    mag = sum(e * e for e in emb) ** 0.5
    return [e / mag for e in emb] if mag > 0 else emb


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if len(v1) != len(v2) or len(v1) == 0:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    m1 = sum(a * a for a in v1) ** 0.5
    m2 = sum(b * b for b in v2) ** 0.5
    return dot / (m1 * m2) if m1 and m2 else 0.0


def extract_patterns_from_file(file_path: str, project_label: str = "") -> List[Pattern]:
    """
    Extract function/class signatures as pattern candidates from a single file.
    Returns a list of Pattern objects.
    """
    lang = _detect_lang(file_path)
    if not lang:
        return []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []

    sigs = _extract_signatures(content, lang)
    patterns: List[Pattern] = []
    for sig in sigs:
        pid = hashlib.md5(f"{file_path}:{sig}".encode()).hexdigest()[:16]
        patterns.append(
            Pattern(
                id=pid,
                pattern_type=PatternType.CODE.value,
                project=project_label or os.path.basename(os.path.dirname(file_path)),
                source_file=file_path,
                code_snippet=sig,
                description=f"{lang} function: {sig}",
                applicability="medium",
            )
        )
    return patterns


def compare_patterns(
    candidates: List[Pattern],
    existing: List[Pattern],
    threshold: float = 0.75,
) -> List[PatternCandidate]:
    """
    Compare new pattern candidates against existing patterns.
    Returns PatternCandidate objects with similarity scores.
    """
    results: List[PatternCandidate] = []
    existing_hashes = [_simple_hash(p.code_snippet) for p in existing]

    for candidate in candidates:
        cand_hash = _simple_hash(candidate.code_snippet)
        best_sim = 0.0
        similar_ids: List[str] = []

        for i, ex_hash in enumerate(existing_hashes):
            sim = _cosine_similarity(cand_hash, ex_hash)
            if sim > best_sim:
                best_sim = sim
            if sim >= threshold:
                similar_ids.append(existing[i].id)

        results.append(
            PatternCandidate(
                pattern=candidate,
                source_project=candidate.project,
                confidence=best_sim,
                similar_to_existing=similar_ids,
                should_promote=best_sim < threshold and len(similar_ids) == 0,
            )
        )

    return results


SURFACE_VERSION = "PGGArchonCrossProjectPatternSurface/v1"
SURFACE_SOURCE = "APEX-AGI omega_pipeline/cross_project_learning.py"
SURFACE_ABSORBED = "2026-05-28"
