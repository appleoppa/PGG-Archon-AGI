from __future__ import annotations

import json

from agent import pgg_archon_evolution_gain_smoke as mod


def test_evidence_score_counts_evidence_not_capability() -> None:
    bridge = {"evidence_summary": {"source_types": {"adapted_external": 1, "official_harness": 1}}}
    smoke = {
        "schema": "PGGArchonAdaptedExternalBenchmarkSmoke/v1",
        "sample_count": 1,
        "items": [{"raw_answer": "FINAL_ANSWER: 2"}],
        "source_sha256": "abc",
    }
    score, reason = mod.evidence_score(bridge_report=bridge, smoke_report=smoke)
    assert score > 0.0
    assert "real_model_outputs_present" in reason
    assert "not model capability gain" in mod.BOUNDARY


def test_evidence_score_without_smoke_stays_partial() -> None:
    bridge = {"evidence_summary": {"source_types": {"adapted_external": 1}}}
    score, reason = mod.evidence_score(bridge_report=bridge, smoke_report=None)
    assert score == 0.25
    assert reason == "adapted_external_source_registered"