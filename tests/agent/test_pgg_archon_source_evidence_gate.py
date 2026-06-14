"""Tests for PGG source evidence gate."""

from __future__ import annotations

from pathlib import Path

from agent.pgg_archon_source_evidence_gate import classify_evidence_card, evaluate_evidence_cards


def test_verified_source_card_allows_promotion_candidate_only() -> None:
    card = {
        "candidate": "AGP",
        "claim": "protocol candidate",
        "source_title": "Autogenesis paper",
        "source_url": "https://example.org/paper",
        "source_type": "paper",
        "evidence_note": "source metadata exists; mechanism still needs extraction",
    }
    ev = classify_evidence_card(card)
    assert ev["status"] == "VERIFIED_SOURCE"
    assert ev["promotion_allowed"] is True


def test_hypothesis_terms_without_source_are_not_promotable() -> None:
    card = {
        "candidate": "APEX_MAX 意识",
        "claim": "L5 consciousness",
        "source_title": "",
        "source_url": "",
        "source_type": "unknown_unverified",
        "evidence_note": "quantum ASI claim",
    }
    ev = classify_evidence_card(card)
    assert ev["status"] == "HYPOTHESIS_ONLY"
    assert ev["promotion_allowed"] is False
    assert ev["hypothesis_flag"] is True


def test_missing_fields_block_promotion() -> None:
    ev = classify_evidence_card({"candidate": "GEPA", "claim": "optimization"})
    assert ev["status"] == "MISSING_SOURCE"
    assert ev["promotion_allowed"] is False
    assert "source_url" in ev["missing_fields"]


def test_evaluate_cards_writes_summary(tmp_path: Path) -> None:
    cards = [
        {
            "candidate": "ApexSpiral",
            "claim": "gene standard",
            "source_title": "local standard",
            "source_url": "file:///tmp/genes.json",
            "source_type": "local_file",
            "evidence_note": "local file reference",
        },
        {"candidate": "APEX_MAX", "claim": "ASI", "source_title": "uploaded", "source_url": "file:///tmp/upload.md", "source_type": "uploaded_note", "evidence_note": "ASI"},
    ]
    out = evaluate_evidence_cards(cards, output_dir=tmp_path)
    assert out["total"] == 2
    assert out["promotion_allowed_count"] == 1
    assert out["counts"]["VERIFIED_SOURCE"] == 1
    assert out["counts"]["PARTIAL_SOURCE"] == 1
    assert Path(out["output_path"]).exists()
