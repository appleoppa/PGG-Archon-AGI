from __future__ import annotations

from pathlib import Path

from agent.apex_gpo import build_gpo_report, coverage, diversity, scan_omega_static, tag_candidate, tag_text


def test_gpo_tags_omega_agi_supremacy_principles():
    assert "P-SCHEDULING" in tag_text("priority scheduler with deadline queue")
    assert "P-CAPABILITY-SECURITY" in tag_text("capability ring security scope")
    assert "P-HEALTH-MONITOR" in tag_text("health snapshot throughput alert monitor")
    assert "P-QUALITY-GATE" in tag_text("CMMI blocking quality gate")


def test_gpo_candidate_coverage_and_diversity():
    candidates = [
        {"name": "Capability security gate candidate"},
        {"name": "Health monitor self healing candidate"},
        {"name": "Swarm consensus pipeline candidate"},
    ]
    report = coverage(candidates)
    assert report["schema"] == "ApexGPOCoverage/v1"
    assert report["covered_count"] >= 4
    assert report["side_effects"] == "read_only_report"
    assert diversity(candidates[0], candidates[1]) >= 0.5


def test_gpo_static_scan_rejects_outside_workspace(tmp_path):
    try:
        scan_omega_static(tmp_path)
    except ValueError as exc:
        assert "workspace" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_gpo_static_scan_omega_agi_supremacy_repo_if_present():
    repo = Path.home() / ".hermes" / "workspace" / "github_repos" / "omega-agi-supremacy"
    report = scan_omega_static(repo)
    assert report["schema"] == "ApexOmegaStaticScan/v2"
    assert report["source_repo"] == "omega-agi-supremacy"
    assert report["side_effects"] == "read_only_report"
    assert report["runtime_allowed"] is False
    if repo.exists():
        assert report["scanned_file_count"] >= 1
        assert report["rs_file_count"] >= 1
        assert report["risk_file_count"] >= 1


def test_gpo_report_is_reference_only():
    report = build_gpo_report()
    assert report["schema"] == "ApexGenePrincipleOntologyReport/v2"
    assert report["source_repo"] == "omega-agi-supremacy"
    assert report["source_policy"] == "reference_only_static_knowledge"
    assert report["principle_count"] >= 10
    assert report["runtime_allowed"] is False
    assert report["absorbed_as"] == "reference_only_static_ontology"
    assert report["side_effects"] == "read_only_report"
