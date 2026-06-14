from __future__ import annotations

from agent.pgg_archon_research_extraction_surface import (
    SURFACE_VERSION,
    SURFACE_SOURCE_HASH,
    build_concept_insights,
    build_pgg_archon_research_extraction_surface,
    extract_key_points,
    normalize_research_sources,
    score_relevance,
)
from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def _sources():
    return [
        {
            "title": "Agent evidence gates",
            "url": "knowledge://agent/evidence",
            "content": "Agent evidence gates require verified sources before promotion. Evidence gates prevent external delivery until proof is complete. The agent must keep an internal report when evidence is missing.",
        },
        {
            "title": "Research extraction",
            "url": "knowledge://agent/research",
            "content": "Research extraction converts caller supplied snippets into summaries and key points. Agent research surfaces must not browse the web or call models automatically.",
        },
    ]


def _build_status_report(research_report):
    return build_pgg_archon_status_surface(
        unlock_report={"schema": "APEXModuleUnlockRegistry/v1", "module_count": 1, "unlockable_count": 1, "agi_completion_claim": False},
        graph_replay_report={"schema": "PGGCaseFlowGraphReplay/v1", "replay_status": "PASS", "next_node": "evidence_gate", "allows_external_delivery": False, "agi_completion_claim": False},
        eval_regression_report={"schema": "PGGEvalRegressionHarness/v1", "status": "PASS", "failed_count": 0, "agi_completion_claim": False},
        golden_regression_report={"schema": "PGGGoldenRegressionReport/v1", "status": "PASS", "failed_expectation_count": 0, "agi_completion_claim": False},
        promotion_guard_report={"schema": "ApexPromotionClaimGuard/v1", "allowed": True, "hold_reasons": [], "agi_completion_claim": False},
        evidence_loop_report={"schema": "PGGArchonEvidenceLoopSurface/v1", "status": "PASS", "missing": [], "agi_completion_claim": False},
        apex_agi_absorption_report={"schema": "PGGArchonApexAGIAbsorptionSurface/v1", "status": "PASS", "ready_candidate_count": 0, "blocking_failures": [], "agi_completion_claim": False},
        p0_surface_report={"schema": "PGGArchonP0Surface/v1", "status": "PASS", "aggregate": {"blocking_failures": [], "surfaces_ok": 3, "surfaces_total": 3}, "agi_completion_claim": False},
        quality_gate_report={"schema": "PGGArchonQualityGateSurface/v1", "status": "PASS", "blocking_failures": [], "warning_failures": [], "agi_completion_claim": False},
        research_extraction_report=research_report,
    )


def test_research_extraction_surface_passes_relevant_sources():
    report = build_pgg_archon_research_extraction_surface(topic="agent evidence gates", sources=_sources())

    assert report["schema"] == SURFACE_VERSION
    assert report["source_hash"] == SURFACE_SOURCE_HASH
    assert report["status"] == "PASS"
    assert report["source_count"] == 2
    assert report["key_point_count"] >= 2
    assert report["relevance"] > 0
    assert report["agi_completion_claim"] is False
    assert report["side_effects"] == "read_only_report"
    assert "No web browsing" in report["boundary"]
    assert "knowledge://agent/evidence" not in str(report["public_sources"])


def test_research_extraction_missing_topic_is_watch_not_pass():
    report = build_pgg_archon_research_extraction_surface(sources=_sources())

    assert report["status"] == "WATCH"
    assert "ResearchTopicMissing" in report["warnings"]
    assert report["key_point_count"] == 0


def test_research_extraction_missing_sources_is_watch_not_pass():
    report = build_pgg_archon_research_extraction_surface(topic="agent evidence")

    assert report["status"] == "WATCH"
    assert "ResearchSourcesMissing" in report["warnings"]
    assert report["source_count"] == 0


def test_research_extraction_json_preview_and_public_source_hashes():
    report = build_pgg_archon_research_extraction_surface(topic="agent research", sources=_sources(), report_format="json")

    assert report["report_format"] == "json"
    assert "key_points" in report["report_preview"]
    assert report["public_sources"][0]["url_hash"]
    assert "knowledge://" not in report["report_preview"]


def test_research_extraction_helpers_score_and_extract_points():
    sources = normalize_research_sources(_sources())
    assert len(sources) == 2
    assert score_relevance("agent evidence gate", "agent evidence") == 1.0
    points = extract_key_points("agent evidence", sources)
    assert any("Evidence gates" in p or "evidence gates" in p for p in points)
    concept_count, insights = build_concept_insights("agent evidence", points)
    assert concept_count > 0
    assert insights


def test_research_extraction_exposes_surface_limits_and_salted_url_hash():
    from agent.pgg_archon_research_extraction_surface import SURFACE_LIMITS, URL_HASH_SALT
    import hashlib

    report = build_pgg_archon_research_extraction_surface(topic="agent evidence", sources=_sources())

    assert report["limits"]["max_sources"] == SURFACE_LIMITS["max_sources"]
    assert report["limits"]["max_report_preview_chars"] == SURFACE_LIMITS["max_report_preview_chars"]
    assert "language_assumption" in report

    plain = hashlib.sha256(b"knowledge://agent/evidence").hexdigest()
    salted = hashlib.sha256((URL_HASH_SALT + ":" + "knowledge://agent/evidence").encode()).hexdigest()
    public_hashes = {src["url_hash"] for src in report["public_sources"]}
    assert salted in public_hashes
    assert plain not in public_hashes


def test_status_surface_accepts_research_extraction_report(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"mode": "ENFORCE", "autopromote_enabled": False, "promotion_count": 0, "stable_ready_count": 0, "pending_rollbacks": 0, "agi_completion_claim": False})
    research = build_pgg_archon_research_extraction_surface(topic="agent evidence gates", sources=_sources())
    report = _build_status_report(research)

    assert report["signals"]["research_extraction_surface_ready"]["ok"] is True
    assert report["summary"]["research_extraction_status"] == "PASS"
    assert report["summary"]["research_extraction_key_point_count"] >= 2
    assert not any(item.get("source") == "pgg_archon_research_extraction_surface" for item in report["small_bottlenecks"])


def test_status_surface_rejects_malformed_research_extraction_report(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"mode": "ENFORCE", "autopromote_enabled": False, "promotion_count": 0, "stable_ready_count": 0, "pending_rollbacks": 0, "agi_completion_claim": False})
    malformed = {"schema": "Wrong/v1", "status": "PASS", "agi_completion_claim": False}
    report = _build_status_report(malformed)

    assert report["signals"]["research_extraction_surface_ready"]["ok"] is False
    assert report["summary"]["research_extraction_schema_ok"] is False
    assert any(item.get("code") == "Res/Schema" for item in report["small_bottlenecks"])


def test_status_surface_research_low_relevance_watch_bottleneck(monkeypatch):
    monkeypatch.setattr("agent.pgg_archon_status_surface.summarize_autonomy_status", lambda: {"mode": "ENFORCE", "autopromote_enabled": False, "promotion_count": 0, "stable_ready_count": 0, "pending_rollbacks": 0, "agi_completion_claim": False})
    low = build_pgg_archon_research_extraction_surface(topic="quantum statute", sources=_sources())
    report = _build_status_report(low)

    assert report["summary"]["research_extraction_status"] == "WATCH"
    assert any(item.get("code") == "Res/Watch" for item in report["small_bottlenecks"])
