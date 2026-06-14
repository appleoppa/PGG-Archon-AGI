"""PGG Archon read-only skill health checker.
Scans ~/.hermes/skills/ for SKILL.md existence and frontmatter validity.
No writes. No manifest creation. No Hermes core mutation.

_NATIVE bridge: Rust PyO3 native module (hermes_pgg_skill_health_checker) ~4x faster.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_NATIVE = False
try:
    import hermes_pgg_skill_health_checker as _native_mod
    _NATIVE = True
except ImportError:
    pass

DEFAULT_SKILLS_DIR = os.path.expanduser("~/.hermes/skills")


@dataclass(frozen=True)
class SkillHealthReport:
    schema: str
    status: str
    total_skills: int
    healthy: int
    with_frontmatter: int
    with_description: int
    with_tags: int
    missing_skills: list[str]
    warnings: list[str]
    detail: str
    evidence_hash: str


if _NATIVE:
    def scan_skills(skills_dir: str = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
        raw = _native_mod.native_scan_skills(skills_dir)
        return json.loads(raw)
else:
    import hashlib
    import re

    def _has_frontmatter(text: str) -> bool:
        return text.strip().startswith("---") and "---" in text.strip()[3:]

    def _parse_frontmatter_field(text: str, field: str) -> bool:
        m = re.search(rf"^{field}\s*:", text, re.MULTILINE)
        return m is not None

    def scan_skills(skills_dir: str = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
        base = Path(skills_dir).expanduser().resolve()
        if not base.is_dir():
            return asdict(SkillHealthReport(
                schema="PGGArchonSkillHealth/v1", status="BLOCKED",
                total_skills=0, healthy=0, with_frontmatter=0, with_description=0,
                with_tags=0, missing_skills=[], warnings=["skills_dir_not_found"],
                detail=f"skills directory not found: {base}", evidence_hash="",
            ))

        all_skill_mds: list[Path] = sorted(base.rglob("SKILL.md"))
        missing: list[str] = []
        healthy = with_fm = with_desc = with_tags = 0

        for md in all_skill_mds:
            if "__pycache__" in md.parts:
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            fm = _has_frontmatter(text)
            desc = _parse_frontmatter_field(text, "description")
            tags = _parse_frontmatter_field(text, "tags")
            if fm and desc:
                healthy += 1
            if fm:
                with_fm += 1
            if desc:
                with_desc += 1
            if tags:
                with_tags += 1

        warnings: list[str] = []
        if missing:
            warnings.append(f"missing_skills={len(missing)}")
        missing_count = len(all_skill_mds) - healthy
        if missing_count > 0:
            warnings.append(f"unhealthy_skills={missing_count}")

        status = "PASS" if healthy == len(all_skill_mds) else "WATCH"
        if not all_skill_mds:
            status = "WATCH"
            warnings.append("no_skills_found")

        payload = "|".join([str(len(all_skill_mds)), str(healthy), str(with_fm)])
        return asdict(SkillHealthReport(
            schema="PGGArchonSkillHealth/v1", status=status,
            total_skills=len(all_skill_mds), healthy=healthy,
            with_frontmatter=with_fm, with_description=with_desc, with_tags=with_tags,
            missing_skills=missing, warnings=warnings,
            detail=f"{healthy}/{len(all_skill_mds)} skills healthy",
            evidence_hash=hashlib.sha256(payload.encode()).hexdigest(),
        ))


__all__ = ["SkillHealthReport", "scan_skills"]