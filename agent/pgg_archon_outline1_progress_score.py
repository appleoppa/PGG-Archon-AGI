"""PGG Archon Outline-1 progress scoring surface.

Reads the DeepSeek/MiniMax 总纲1 scoring artifacts and normalizes them into a
bounded, reusable status surface. This module intentionally distinguishes:
  - valid structured model scores
  - visible but unstructured/parse-failed LLM outputs
  - engineering status surface (33/33 ACTIVE)
  - real AGI capability level (L0-L5)

Boundary: LLM-as-judge evidence, not an official AGI benchmark.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HOME = Path.home()
DEFAULT_SCORE_PATH = HOME / ".hermes/workspace/audit/p3_outline1_score_20260604/deepseek_minimax_score.json"
DEFAULT_REPORT_PATH = HOME / ".hermes/workspace/audit/p3_outline1_score_20260604/outline1_progress_comparison_report.json"
DEFAULT_MANIFEST_PATH = HOME / ".hermes/data/EVOLUTION_MANIFEST.json"

LEVEL_RANGES = {
    "L0": (0, 30),
    "L1": (31, 50),
    "L2": (51, 70),
    "L3": (71, 85),
    "L4": (86, 94),
    "L5": (95, 100),
}


@dataclass(frozen=True)
class Outline1Progress:
    status: str
    score: float | None
    level: str | None
    valid_structured_providers: list[str]
    invalid_or_unstructured_providers: list[str]
    dimension_scores: dict[str, float]
    final_33_active: bool
    provider_success: dict[str, int]
    boundary: str
    score_path: str
    report_path: str


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def level_for_score(score: float | int | None) -> str | None:
    if score is None:
        return None
    s = float(score)
    for level, (lo, hi) in LEVEL_RANGES.items():
        if lo <= s <= hi:
            return level
    return None


def collect_outline1_progress(
    score_path: Path = DEFAULT_SCORE_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> Outline1Progress:
    score_doc = _load_json(score_path)
    report_doc = _load_json(report_path)
    manifest = _load_json(manifest_path)
    final_key = manifest.get("summary", {}).get("latest_p3_final_33_active_20260604", {})

    providers = score_doc.get("providers", {})
    valid: list[str] = []
    invalid: list[str] = []
    parsed_scores: list[float] = []
    dimension_scores: dict[str, float] = {}

    for name, rec in providers.items():
        parsed = rec.get("parsed") if isinstance(rec, dict) else None
        if isinstance(parsed, dict) and isinstance(parsed.get("overall_score"), (int, float)):
            valid.append(name)
            parsed_scores.append(float(parsed["overall_score"]))
            if not dimension_scores and isinstance(parsed.get("dimension_scores"), dict):
                dimension_scores = {str(k): float(v) for k, v in parsed["dimension_scores"].items() if isinstance(v, (int, float))}
        else:
            invalid.append(name)

    if not parsed_scores and isinstance(report_doc.get("objective_summary"), dict):
        score = report_doc["objective_summary"].get("structured_score")
        if isinstance(score, (int, float)):
            parsed_scores.append(float(score))
    score = sum(parsed_scores) / len(parsed_scores) if parsed_scores else None
    level = level_for_score(score)

    status_dist = final_key.get("status_distribution", {})
    final_33_active = status_dist == {"SKELETON": 0, "ABSENT": 0, "PARTIAL": 0, "ACTIVE": 33}
    status = "COMPLETE_L1_EVIDENCE" if final_33_active and level == "L1" else "WATCH"

    return Outline1Progress(
        status=status,
        score=score,
        level=level,
        valid_structured_providers=valid,
        invalid_or_unstructured_providers=invalid,
        dimension_scores=dimension_scores,
        final_33_active=final_33_active,
        provider_success={str(k): int(v) for k, v in final_key.get("provider_success", {}).items() if isinstance(v, int)},
        boundary="Outline-1 score is LLM-as-judge evidence; 33-card ACTIVE is engineering status surface, not full AGI.",
        score_path=str(score_path),
        report_path=str(report_path),
    )


def main() -> int:
    print(json.dumps(asdict(collect_outline1_progress()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
