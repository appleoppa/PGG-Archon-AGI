from __future__ import annotations

from agent.pgg_archon_outline1_progress_score import collect_outline1_progress, level_for_score


def test_level_for_score_boundaries() -> None:
    assert level_for_score(30) == "L0"
    assert level_for_score(34) == "L1"
    assert level_for_score(70) == "L2"
    assert level_for_score(85) == "L3"
    assert level_for_score(94) == "L4"
    assert level_for_score(100) == "L5"


def test_collect_outline1_progress_reads_current_artifacts() -> None:
    p = collect_outline1_progress()
    assert p.final_33_active is True
    assert p.score == 34.0
    assert p.level == "L1"
    assert "deepseek" in p.valid_structured_providers
    assert "minimax" in p.invalid_or_unstructured_providers
    assert p.dimension_scores["基础认知"] == 9.0
