from __future__ import annotations

import json

from agent.pgg_archon_engineering_factor_gate import (
    BOUNDARY,
    evaluate_engineering_factor_card,
    evaluate_engineering_factor_cards,
)


def _valid_card(source_status: str = "VERIFIED_SOURCE") -> dict:
    return {
        "id": "factor.demo",
        "source_status": source_status,
        "source_url": "https://github.com/example/repo",
        "commit_sha": "abc123",
        "read_scope": "metadata_and_selected_files_only",
        "source_files": ["README.md"],
        "extracted_engineering_factors": [
            {"name": "bounded_gate", "observed": True, "evidence": "README describes gate"}
        ],
        "pgg_mapping": {"target": "internal_gate"},
        "allowed_use": "pattern absorption",
        "blocked_claims": ["official external benchmark", "full AGI"],
    }


def test_verified_source_card_allows_official_source_candidate() -> None:
    result = evaluate_engineering_factor_card(_valid_card("VERIFIED_SOURCE"))

    assert result["valid"] is True
    assert result["promotion_allowed"] is True
    assert result["official_source_claim_allowed"] is True
    assert result["boundary"] == BOUNDARY


def test_repro_impl_remains_pattern_only_and_cannot_promote() -> None:
    card = _valid_card("REPRO_IMPL")
    card["promote"] = True

    result = evaluate_engineering_factor_card(card)

    assert result["valid"] is False
    assert "repro_or_artifact_cannot_promote" in result["errors"]
    assert result["promotion_allowed"] is False
    assert result["official_source_claim_allowed"] is False


def test_missing_observed_evidence_is_invalid() -> None:
    card = _valid_card("PARTIAL_SOURCE")
    card["extracted_engineering_factors"] = [{"name": "factor", "observed": True}]

    result = evaluate_engineering_factor_card(card)

    assert result["valid"] is False
    assert "observed_factor_missing_evidence:0" in result["errors"]


def test_batch_writes_output_file(tmp_path) -> None:
    summary = evaluate_engineering_factor_cards([_valid_card(), _valid_card("SOURCE_ARTIFACT")], output_dir=tmp_path)

    assert summary["schema"] == "PGGEngineeringFactorGate/v1"
    assert summary["total"] == 2
    assert summary["invalid"] == 0
    assert summary["promotion_allowed_count"] == 1
    output_path = tmp_path / summary["output_path"].split("/")[-1]
    assert output_path.exists()
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded["boundary"] == BOUNDARY
