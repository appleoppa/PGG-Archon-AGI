"""Tests for GitHub source closure gate."""

from __future__ import annotations

from agent.pgg_archon_github_source_closure_gate import evaluate_github_source_card, evaluate_github_source_cards


def test_verified_requires_bidirectional_official_closure() -> None:
    ev = evaluate_github_source_card({
        "target_name": "official",
        "repo_url": "https://github.com/org/repo",
        "commit_sha": "abc",
        "paper_to_repo_evidence_strong": True,
        "repo_to_paper_evidence_strong": True,
        "author_org_match_strong": True,
        "core_content_paths": ["src/main.py"],
        "timeline_reasonable": True,
        "license_citation_present": True,
        "noise_exclusion_done": True,
    })
    assert ev["status"] == "VERIFIED_SOURCE"
    assert ev["confidence"] >= 85


def test_missing_commit_blocks_verified() -> None:
    ev = evaluate_github_source_card({"target_name": "floating", "repo_url": "https://github.com/org/repo"})
    assert ev["status"] == "MISSING"
    assert "commit_sha_missing" in ev["veto_flags"]


def test_inspired_by_is_repro_impl_even_with_core_paths() -> None:
    ev = evaluate_github_source_card({
        "target_name": "inspired",
        "repo_url": "https://github.com/u/r",
        "commit_sha": "abc",
        "explicit_unofficial_or_inspired_by": True,
        "repo_to_paper_evidence_strong": True,
        "core_content_paths": ["src", "tests"],
        "timeline_reasonable": True,
        "noise_exclusion_done": True,
    })
    assert ev["status"] == "REPRO_IMPL"
    assert "explicit_unofficial_or_inspired_by" in ev["veto_flags"]


def test_local_artifact_is_source_artifact() -> None:
    ev = evaluate_github_source_card({"target_name": "artifact", "local_only_artifact": True, "commit_sha": "sha256:abc"})
    assert ev["status"] == "SOURCE_ARTIFACT"


def test_partial_when_one_way_evidence_and_core_paths() -> None:
    ev = evaluate_github_source_card({
        "target_name": "partial",
        "repo_url": "https://github.com/u/r",
        "commit_sha": "abc",
        "repo_to_paper_evidence_strong": True,
        "core_content_paths": ["paper.md"],
        "timeline_reasonable": True,
        "noise_exclusion_done": True,
    })
    assert ev["status"] == "PARTIAL_SOURCE"


def test_batch_counts(tmp_path) -> None:
    out = evaluate_github_source_cards([
        {"target_name": "artifact", "local_only_artifact": True, "commit_sha": "sha256:abc"},
        {"target_name": "missing"},
    ], output_dir=tmp_path)
    assert out["total"] == 2
    assert out["counts"]["SOURCE_ARTIFACT"] == 1
    assert out["counts"]["MISSING"] == 1
    assert out["verified_count"] == 0
    assert "output_path" in out
